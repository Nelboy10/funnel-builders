import abc

class BasePaymentGateway(abc.ABC):
    """
    Abstract base class for all payment gateways (Stripe, PayPal, FedaPay, etc.)
    """

    @abc.abstractmethod
    def create_payment_intent(self, user, course):
        pass

    @abc.abstractmethod
    def verify_payment(self, payment_reference):
        pass
