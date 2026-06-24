class Styles:
    GLOBAL = """
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    
    :root {
        --primary: #8a63ff;
        --secondary: #4a3f5f;
        --bg: #0b0b1a;
        --text: #e0e0e6;
        --accent: #ff00ea;
        --glass: rgba(255, 255, 255, 0.04);
        --glass-border: rgba(255, 255, 255, 0.1);
        --container-px: 40px;
    }

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    body {
        background-color: var(--bg);
        color: var(--text);
        overflow-x: hidden;
        min-height: 100vh;
    }

    /* Effects */
    .star-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        background: radial-gradient(ellipse at bottom, #1b2735 0%, #090a0f 100%);
    }

    .star {
        position: absolute;
        background: white;
        border-radius: 50%;
        opacity: 0.5;
        animation: twinkle var(--duration) infinite ease-in-out;
    }

    @keyframes twinkle {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.2); }
    }

    .comet {
        position: absolute;
        top: var(--top);
        left: var(--left);
        height: 2px;
        background: linear-gradient(-45deg, #fff, rgba(0, 0, 255, 0));
        filter: drop-shadow(0 0 6px #fff);
        opacity: 0;
        z-index: -1;
        animation: shooting var(--duration) linear infinite;
        animation-delay: var(--delay);
    }

    @keyframes shooting {
        0% { transform: rotate(-45deg) translateX(0); opacity: 0; width: 0; }
        1% { opacity: 1; }
        20% { transform: rotate(-45deg) translateX(-500px); opacity: 0; width: 150px; }
        100% { transform: rotate(-45deg) translateX(-500px); opacity: 0; width: 150px; }
    }

    /* Typography */
    h1 { font-size: clamp(3rem, 10vw, 5.5rem); font-weight: 900; letter-spacing: -3px; }
    h2 { font-size: clamp(2rem, 7vw, 3rem); font-weight: 800; letter-spacing: -1px; }
    h3 { font-size: 1.4rem; font-weight: 700; }

    /* Layout */
    .container {
        width: 100%;
        max-width: 1400px;
        margin: 0 auto;
        padding: 0 var(--container-px);
    }

    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 25px;
    }

    /* UI Components */
    .glass {
        background: var(--glass);
        backdrop-filter: blur(15px);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .glass:hover {
        background: rgba(255, 255, 255, 0.07);
        border-color: rgba(138, 99, 255, 0.4);
        transform: translateY(-5px);
    }

    .btn {
        padding: 14px 30px;
        border-radius: 16px;
        font-weight: 800;
        text-decoration: none;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        cursor: pointer;
        font-size: 0.95rem;
    }

    .btn-primary {
        background: linear-gradient(135deg, var(--primary), var(--accent));
        color: white;
        box-shadow: 0 10px 25px rgba(138, 99, 255, 0.3);
        border: none;
    }

    .btn-primary:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 15px 30px rgba(138, 99, 255, 0.5);
    }

    /* Header */
    .main-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 40px;
        position: sticky;
        top: 0;
        z-index: 1000;
        background: rgba(10, 10, 15, 0.8);
        backdrop-filter: blur(25px);
        border-bottom: 1px solid var(--glass-border);
        height: 80px;
    }

    .nav-bar {
        display: flex;
        gap: 8px;
        padding: 6px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--glass-border);
        border-radius: 18px;
    }

    .nav-btn {
        width: 46px;
        height: 46px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 14px;
        color: #808090;
        text-decoration: none;
        transition: all 0.2s ease;
    }

    .nav-btn:hover { background: rgba(255, 255, 255, 0.06); color: white; }
    .nav-btn.active { background: var(--primary); color: white; box-shadow: 0 5px 15px rgba(138, 99, 255, 0.4); }

    /* User Profile & Dropdown */
    .user-profile-container { position: relative; display: flex; align-items: center; }
    .user-pfp-wrapper { position: relative; cursor: pointer; padding: 2px; border-radius: 50%; transition: all 0.3s ease; border: 2px solid transparent; }
    .user-pfp-wrapper:hover { border-color: var(--primary); transform: scale(1.05); }
    .user-avatar-nav { width: 38px; height: 38px; border-radius: 50%; display: block; object-fit: cover; }

    .online-indicator {
        position: absolute;
        bottom: 2px;
        right: 2px;
        width: 12px;
        height: 12px;
        background: #23a55a;
        border: 2px solid #0b0b1a;
        border-radius: 50%;
    }

    .user-dropdown {
        position: absolute;
        top: calc(100% + 15px);
        right: 0;
        width: 240px;
        background: rgba(15, 15, 25, 0.98);
        backdrop-filter: blur(25px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 15px;
        box-shadow: 0 15px 50px rgba(0,0,0,0.8);
        z-index: 2000;
        overflow: hidden;
    }

    .dropdown-header { padding: 5px 10px 15px; border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 10px; overflow: hidden; }
    .dropdown-user-name { font-weight: 800; font-size: 1rem; color: white; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .dropdown-user-handle { font-size: 0.75rem; color: #606070; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .dropdown-item { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 12px; text-decoration: none; color: #a0a0b0; font-size: 0.9rem; font-weight: 600; transition: all 0.2s ease; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .dropdown-item:hover { background: rgba(255,255,255,0.05); color: white; }
    .logout-btn:hover { background: rgba(255, 71, 87, 0.1) !important; color: #ff4757 !important; }

    /* Hero */
    .hero {
        min-height: 85vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 100px 0;
    }

    .hero h1 {
        background: linear-gradient(135deg, #fff 40%, var(--primary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 25px;
    }

    .hero p {
        font-size: 1.25rem;
        max-width: 750px;
        color: #9090a0;
        line-height: 1.7;
        margin-bottom: 45px;
    }

    /* Feature Cards */
    .feature-card {
        padding: 45px;
        display: flex;
        flex-direction: column;
        gap: 20px;
        text-align: left;
    }

    .feature-icon-wrapper {
        width: 60px;
        height: 60px;
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(138, 99, 255, 0.15);
        color: var(--primary);
        margin-bottom: 10px;
    }

    /* Sub-pages Responsive */
    .docs-container { display: grid; grid-template-columns: 320px 1fr; gap: 50px; margin: 80px auto; }
    .docs-sidebar { position: sticky; top: 110px; height: calc(100vh - 150px); padding: 35px 25px; }
    .docs-content { padding: 50px; line-height: 1.8; }

    /* Leaderboard */
    .leaderboard-row { display: flex; align-items: center; padding: 18px 30px; gap: 20px; border-radius: 20px; margin-bottom: 12px; }
    .user-avatar-small { width: 52px; height: 52px; border-radius: 50%; border: 2px solid rgba(255, 255, 255, 0.1); }

    /* Embed Builder */
    .builder-container { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin: 60px auto; }
    .builder-input { width: 100%; padding: 15px 20px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 14px; color: white; outline: none; }

    @media (max-width: 1200px) {
        .builder-container { grid-template-columns: 1fr; }
        .docs-container { grid-template-columns: 1fr; }
        .docs-sidebar { position: relative; top: 0; height: auto; }
    }

    @media (max-width: 768px) {
        :root { --container-px: 20px; }
        .desktop-only { display: none; }
        .main-header { padding: 0 20px; height: 70px; }
        
        .nav-bar {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 3000;
            background: rgba(15, 15, 25, 0.95);
            border-radius: 24px;
            padding: 8px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.8);
        }

        .nav-btn { width: 42px; height: 42px; }
        .hero { padding: 60px 0; }
        .feature-card { padding: 35px 25px; }
        .stats-group { flex-direction: column; align-items: flex-end; gap: 4px; }
        .user-id { display: none; }
    }

    .footer { padding: 100px 0 60px; text-align: center; opacity: 0.8; }
    main { padding-bottom: 100px; }
    @media (min-width: 769px) { main { padding-bottom: 0; } }
    """
