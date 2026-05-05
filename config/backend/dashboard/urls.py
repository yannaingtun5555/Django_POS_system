from django.urls import path
from .views import (
    totalsale_profit_transcation,
    rollingdailysale,
    lowstock,
    topsellings,
    recentactivity,
)

urlpatterns = [
    path("totalsale_profit_transcation/",totalsale_profit_transcation,name = "totalsale-profit-transction"),
    path("rollingdailysale/",rollingdailysale,name = "rolling-daily-sale"),
    path("lowstock/",lowstock,name = "lowstock"),
    path("topsellings/",topsellings ,name = "topsellings"),
    path("recentactivity/",recentactivity ,name = "recentactivity"),
]
