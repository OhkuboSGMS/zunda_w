import platform


def alert():
    if platform.system() == 'Windows':
        import winsound
        winsound.PlaySound("SystemNotification", winsound.SND_ALIAS)
