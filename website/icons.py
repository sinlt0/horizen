import base64

class Icons:
    # Solid 2.0 stroke and explicit dimensions for maximum stability
    _BASE = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    
    HOME = f'{_BASE}<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>'
    LIST = f'{_BASE}<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg>'
    
    # Ultra-stable Users design
    USERS = f'{_BASE}<path d="M14 19a6 6 0 0 0-12 0"/><circle cx="8" cy="9" r="4"/><path d="M22 19a6 6 0 0 0-6-6 4 4 0 1 0 0-8"/></svg>'
    
    BOOK = f'{_BASE}<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M8 7h6"/><path d="M8 11h8"/></svg>'
    
    # Cleanest possible Rocket design
    ROCKET = f'{_BASE}<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.71.71-2.5.71-2.5h-2.42c0 0-1.29 0-1.29-1.29V14c0-1.29 0-1.29 1.29-1.29h2.42s0-1.79.71-2.5c1.26-1.5 5-2 5-2s-.5 3.74-2 5c-.71.71-2.5.71-2.5.71v2.42s0 1.29-1.29 1.29H14c-1.29 0-1.29 0-1.29-1.29v-2.42s-1.79 0-2.5.71Z"/></svg>'
    
    CODE = f'{_BASE}<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>'
    FOLDER = f'{_BASE}<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg>'
    USER = f'{_BASE}<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
    CROWN = f'{_BASE}<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/></svg>'
    WAND = f'{_BASE}<path d="m19 2 5 5M2 22l5-5m1.5 1.5 5-5m1.5 1.5 5-5m-12-2L14 3m-9 9 11-11M3 14l11-11M2 16l11-11"/></svg>'

    # Categories
    CONFIG = f'{_BASE}<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.58a2 2 0 0 1-1.73 1h-.18a2 2 0 0 0-2 2v.44a2 2 0 0 0 2 2h.18a2 2 0 0 1 1.73 1l.43.58a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.58a2 2 0 0 1 1.73-1h.18a2 2 0 0 0 2-2v-.44a2 2 0 0 0-2-2h-.18a2 2 0 0 1-1.73-1l-.43-.58a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>'
    INFO = f'{_BASE}<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>'
    MODERATION = f'{_BASE}<path d="M11 13 3 3"/><path d="m9 7 8 8"/><path d="m21 11-8-8"/><path d="m16 16 6-6"/><path d="m8 8 6-6"/><path d="m14.5 12.5-8 8a2.11 2.11 0 1 1-3-3l8-8"/></svg>'
    SECURITY = f'{_BASE}<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>'
    ANTINUKE = f'{_BASE}<circle cx="12" cy="12" r="10"/><path d="M12 2v4"/><path d="M12 18v4"/><path d="m4.9 4.9 2.9 2.9"/><path d="m16.2 16.2 2.9 2.9"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="m4.9 19.1 2.9-2.9"/><path d="m16.2 7.8 2.9-2.9"/></svg>'
    AUTOMOD = f'{_BASE}<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>'
    VOICEMASTER = f'{_BASE}<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>'
    GENERAL = f'{_BASE}<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>'
    SOCIAL = f'{_BASE}<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>'
    FUN = f'{_BASE}<rect width="20" height="12" x="2" y="6" rx="2"/><path d="M9 12h.01"/><path d="M15 12h.01"/><path d="M12 15h.01"/></svg>'
    LOGGING = f'{_BASE}<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14.5 2 14.5 7.5 20 7.5"/><line x1="10" x2="16" y1="13" y2="13"/><line x1="10" x2="16" y1="17" y2="17"/></svg>'
    NSFW = f'{_BASE}<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.52 13.16 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>'
    SHIELD = f'{_BASE}<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
    ZAP = f'{_BASE}<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
    TERMINAL = f'{_BASE}<polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>'
    TICKET = f'{_BASE}<path d="M2 9V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4"/><path d="M2 15v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4"/><path d="M2 9a3 3 0 0 1 0 6"/><path d="M22 9a3 3 0 0 0 0 6"/><line x1="13" x2="13" y1="3" y2="21"/></svg>'
    GIFT = f'{_BASE}<polyline points="20 12 20 22 4 22 4 12"/><rect width="20" height="5" x="2" y="7"/><line x1="12" x2="12" y1="22" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg>'
    SHIELD_CHECK = f'{_BASE}<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>'
    INVITE = f'{_BASE}<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
    THREAD = f'{_BASE}<path d="m9 10 2 2 4-4"/><rect width="20" height="20" x="2" y="2" rx="5"/></svg>'
    WEBHOOK = f'{_BASE}<path d="M10 2v8l-8 4V2a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2z"/><path d="M2 14l8-4v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/></svg>'
    EMOJI = f'{_BASE}<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" x2="9.01" y1="9" y2="9"/><line x1="15" x2="15.01" y1="9" y2="9"/></svg>'

    @staticmethod
    def b64(html_str):
        return base64.b64encode(html_str.encode()).decode()
