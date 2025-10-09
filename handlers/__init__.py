from . import start, payment, subscription, admin

routers = [
    start.router,
    admin.router,
    payment.router,
    subscription.router,
]
