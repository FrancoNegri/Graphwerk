"""Scripted demo: sample repo + shadow worktree with staged changes + rationale.

Simulates the state after telling Claude: "add payment validation and retries
to checkout, print receipts, and drop the deprecated helper" — without needing
a live session. Exercises every node state: modified, added, deleted, affected.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

BASE_FILES = {
    "shop/__init__.py": "",
    "shop/models.py": '''from dataclasses import dataclass, field


@dataclass
class User:
    name: str
    email: str


@dataclass
class Order:
    user: User
    items: list = field(default_factory=list)

    def total(self):
        return sum(item["price"] * item["qty"] for item in self.items)
''',
    "shop/payment.py": '''class PaymentError(Exception):
    pass


class PaymentGateway:
    def __init__(self, api_key):
        self.api_key = api_key

    def charge(self, order, amount):
        response = self._send({"order": id(order), "amount": amount})
        if response["status"] != "ok":
            raise PaymentError(response["reason"])
        return response["txn_id"]

    def _send(self, payload):
        return {"status": "ok", "txn_id": "txn-123"}
''',
    "shop/checkout.py": '''from shop.models import Order
from shop.payment import PaymentGateway
from shop.utils import format_price


class CheckoutService:
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway

    def checkout(self, order: Order):
        amount = order.total()
        txn_id = self.gateway.charge(order, amount)
        return {"txn": txn_id, "display": format_price(amount)}
''',
    "shop/utils.py": '''def format_price(amount):
    return f"${amount:,.2f}"


def deprecated_helper(x):
    return x
''',
    "shop/refunds.py": '''from shop.payment import PaymentGateway


class RefundService:
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway

    def refund(self, order, amount):
        return self.gateway.charge(order, -amount)
''',
}

STAGED_FILES = {
    "shop/payment.py": '''import time


class PaymentError(Exception):
    pass


class PaymentValidator:
    def validate(self, order, amount):
        if amount <= 0:
            raise PaymentError("amount must be positive")
        if not order.items:
            raise PaymentError("cannot charge an empty order")


class PaymentGateway:
    MAX_RETRIES = 3

    def __init__(self, api_key):
        self.api_key = api_key

    def charge(self, order, amount):
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            response = self._send({"order": id(order), "amount": amount})
            if response["status"] == "ok":
                return response["txn_id"]
            last_error = response["reason"]
            time.sleep(2 ** attempt)
        raise PaymentError(f"charge failed after {self.MAX_RETRIES} attempts: {last_error}")

    def _send(self, payload):
        return {"status": "ok", "txn_id": "txn-123"}
''',
    "shop/checkout.py": '''from shop.models import Order
from shop.payment import PaymentGateway, PaymentValidator
from shop.receipts import ReceiptPrinter
from shop.utils import format_price


class CheckoutService:
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway
        self.validator = PaymentValidator()

    def checkout(self, order: Order):
        amount = order.total()
        self.validator.validate(order, amount)
        txn_id = self.gateway.charge(order, amount)
        receipt = ReceiptPrinter().print_receipt(order, txn_id)
        return {"txn": txn_id, "display": format_price(amount), "receipt": receipt}
''',
    "shop/utils.py": '''def format_price(amount):
    return f"${amount:,.2f}"
''',
    "shop/receipts.py": '''from shop.utils import format_price


class ReceiptPrinter:
    def print_receipt(self, order, txn_id):
        lines = [f"Receipt for {order.user.name} (txn {txn_id})"]
        for item in order.items:
            lines.append(f'  {item["name"]}: {format_price(item["price"] * item["qty"])}')
        lines.append(f"  Total: {format_price(order.total())}")
        return "\\n".join(lines)
''',
}

RATIONALE = {
    "shop/payment.py::PaymentValidator": "New validation layer so bad orders are rejected before hitting the gateway — previously an empty order produced a confusing gateway error.",
    "shop/payment.py::PaymentGateway.charge": "Transient gateway failures were dropping orders. Added up to 3 retries with exponential backoff; only raises after all attempts fail.",
    "shop/payment.py::PaymentGateway": "Hosts the new MAX_RETRIES knob used by charge().",
    "shop/checkout.py::CheckoutService.checkout": "Wired in validation before charging and receipt printing after, per the feature request.",
    "shop/checkout.py::CheckoutService.__init__": "CheckoutService now owns a PaymentValidator instance.",
    "shop/checkout.py::CheckoutService": "Checkout now validates first and returns a printable receipt.",
    "shop/receipts.py::ReceiptPrinter": "New class for the receipt feature — kept separate from checkout so other flows (refunds) can reuse it.",
    "shop/receipts.py": "New module for receipt rendering.",
    "shop/utils.py::deprecated_helper": "Removed: no remaining callers, flagged deprecated for two releases.",
    "shop/utils.py": "Dropped the deprecated helper; format_price is untouched.",
    "shop/payment.py": "Payment layer gains validation and retry logic.",
    "shop/checkout.py": "Checkout orchestrates the new validation and receipt steps.",
}


def build_demo(workspace: Path) -> tuple[Path, Path, Path]:
    """(Re)create demo repo + staged worktree. Returns (base, staged, sidecar)."""
    base = workspace / "repo"
    staged = workspace / "staged"
    if workspace.exists():
        shutil.rmtree(workspace)
    base.mkdir(parents=True)

    for rel, content in BASE_FILES.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    _git(base, "init", "-q", "-b", "main")
    _git(base, "add", "-A")
    _git(base, "-c", "user.email=demo@graphwerk.local", "-c", "user.name=graphwerk demo", "commit", "-qm", "initial shop app", "--no-verify")
    _git(base, "worktree", "add", "-q", "-B", "graphwerk-staging", str(staged))

    for rel, content in STAGED_FILES.items():
        (staged / rel).write_text(content, encoding="utf-8")

    graphwerk_dir = staged / ".graphwerk"
    graphwerk_dir.mkdir(exist_ok=True)
    sidecar = graphwerk_dir / "rationale.json"
    sidecar.write_text(json.dumps(RATIONALE, indent=2), encoding="utf-8")
    return base, staged, sidecar


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)
