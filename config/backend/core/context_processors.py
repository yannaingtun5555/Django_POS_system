from constance import config


def app_config(request):
    return {
        "shop_name": getattr(config, "SHOP_NAME", "BananiPOS"),
        "currency_prefix": getattr(config, "CURRENCY_PREFIX", "$"),
        "currency_postfix": getattr(config, "CURRENCY_POSTFIX", ""),
    }
