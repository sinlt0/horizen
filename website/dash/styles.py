class DashStyles:
    DASHBOARD = """
    /* Global Dashboard Reset */
    * { box-sizing: border-box; }
    
    .dash-container {
        display: grid;
        grid-template-columns: 280px 1fr;
        min-height: calc(100vh - 80px);
        background: rgba(0, 0, 0, 0.4);
        overflow-x: hidden;
    }

    .dash-sidebar {
        background: rgba(10, 10, 20, 0.6);
        backdrop-filter: blur(25px);
        border-right: 1px solid var(--glass-border);
        padding: 30px 20px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        position: sticky;
        top: 80px;
        height: calc(100vh - 80px);
        z-index: 100;
    }

    .dash-nav-item {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 12px 18px;
        border-radius: 12px;
        color: #808090;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.2s ease;
        border: 1px solid transparent;
        font-size: 0.9rem;
    }

    .dash-nav-item svg { width: 18px; height: 18px; opacity: 0.7; }

    .dash-nav-item:hover { background: rgba(255, 255, 255, 0.05); color: white; }
    .dash-nav-item.active { background: rgba(138, 99, 255, 0.12); color: var(--primary); border-color: rgba(138, 99, 255, 0.2); }
    .dash-nav-item.active svg { opacity: 1; color: var(--primary); }

    .dash-content {
        padding: 60px 40px; /* High top padding to clear sticky elements */
        max-width: 1300px;
        width: 100%;
        margin: 0 auto;
        min-height: calc(100vh - 80px);
        display: flex;
        flex-direction: column;
        gap: 30px;
    }

    /* Professional Card System */
    .module-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        width: 100%;
        overflow: hidden;
    }

    /* Form Controls */
    .input-group { margin-bottom: 25px; }
    .input-label { display: block; font-size: 0.75rem; font-weight: 800; color: #606070; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; }
    .dash-input, .dash-select, .dash-textarea {
        width: 100%;
        padding: 12px 18px;
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        color: white;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        outline: none;
    }
    .dash-input:focus, .dash-textarea:focus { border-color: var(--primary); background: rgba(0,0,0,0.6); }

    /* Mobile Adaptations */
    .dash-mobile-nav {
        display: none;
        gap: 10px;
        overflow-x: auto;
        padding: 12px 20px;
        background: rgba(10, 10, 20, 0.9);
        backdrop-filter: blur(15px);
        border-bottom: 1px solid var(--glass-border);
        scrollbar-width: none;
        position: sticky;
        top: 70px;
        z-index: 900;
    }

    .mobile-nav-item {
        flex: 0 0 auto;
        padding: 10px 16px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.03);
        color: #a0a0b0;
        text-decoration: none;
        font-size: 0.8rem;
        font-weight: 700;
        border: 1px solid var(--glass-border);
    }
    .mobile-nav-item.active { background: var(--primary); color: white; border-color: transparent; }

    @media (max-width: 1024px) {
        .dash-container { grid-template-columns: 1fr; }
        .dash-sidebar { display: none; }
        .dash-mobile-nav { display: flex; }
        .dash-content { padding: 40px 20px 120px; } /* Ensures bottom nav doesn't hide content */
    }

    /* Save Changes Bar */
    .save-bar {
        position: fixed;
        bottom: 25px;
        left: 50%;
        transform: translateX(-50%) translateY(150px);
        width: 90%;
        max-width: 900px;
        background: rgba(20, 20, 30, 0.95);
        backdrop-filter: blur(20px);
        border: 1px solid var(--primary);
        border-radius: 18px;
        padding: 16px 25px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 5000;
        transition: transform 0.6s cubic-bezier(0.19, 1, 0.22, 1);
        box-shadow: 0 20px 50px rgba(0,0,0,0.6), 0 0 20px rgba(138, 99, 255, 0.2);
    }
    .save-bar.visible { transform: translateX(-50%) translateY(0); }

    /* Discord Mockup */
    .discord-view { background: #313338; border-radius: 8px; padding: 20px; font-family: 'Whitney', sans-serif; }
    .discord-msg { display: flex; gap: 16px; }
    .discord-avatar { width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; }
    .discord-content { flex: 1; min-width: 0; }
    .discord-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .discord-name { font-weight: 600; color: white; }
    .discord-bot-tag { background: #5865f2; color: white; font-size: 0.65rem; padding: 1px 4px; border-radius: 3px; font-weight: 600; }
    .discord-embed { background: #2b2d31; border-left: 4px solid var(--primary); border-radius: 4px; padding: 12px 16px; margin-top: 8px; max-width: 520px; }
    .discord-embed-title { font-weight: 600; color: #00a8fc; font-size: 1rem; margin-bottom: 8px; }
    .discord-embed-description { font-size: 0.875rem; color: #dbdee1; line-height: 1.375; }

    /* Guild Selection */
    .guild-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 30px; margin-top: 40px; }
    .guild-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 35px 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        text-decoration: none;
        color: white;
    }
    .guild-card:hover { transform: translateY(-10px); background: rgba(138, 99, 255, 0.08); border-color: var(--primary); box-shadow: 0 20px 40px rgba(0,0,0,0.4); }
    .guild-icon-lg, .guild-icon-placeholder { width: 100px; height: 100px; border-radius: 35px; object-fit: cover; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #1a1a2e, #8a63ff); color: white; border: 2px solid rgba(255,255,255,0.1); }
    .guild-name-text { font-weight: 800; font-size: 1.2rem; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 10px; }
    .btn-manage-small { font-size: 0.75rem; font-weight: 800; color: var(--primary); padding: 8px 25px; border-radius: 12px; background: rgba(138, 99, 255, 0.1); border: 1px solid rgba(138, 99, 255, 0.2); transition: all 0.3s ease; }
    .guild-card:hover .btn-manage-small { background: var(--primary); color: white; }
    """
