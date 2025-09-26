from . import start, payment, subscription, admin

routers = [
    start.router,
    payment.router,
    subscription.router,
    admin.router
]
