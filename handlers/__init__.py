from . import start, info, payment, subscription

routers = [
    start.router,
    payment.router,
    subscription.router,
    info.router
]
