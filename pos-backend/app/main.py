from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from . import models
from .database import engine
from .routers import sync, products, auth, analytics, admin

app = FastAPI(title="Faida POS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(sync.router)
app.include_router(products.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def landing():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>Faida — Duka yako, faida yako</title>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, -apple-system, sans-serif;
               background: #0f1f14; color: #fff; }

        /* Nav */
        nav { display: flex; justify-content: space-between; align-items: center;
              padding: 20px 40px; }
        .nav-logo { font-weight: 900; font-size: 22px; letter-spacing: 3px;
                    color: #fff; }
        .nav-cta { background: #C2703D; color: #fff; border: none; padding: 10px 22px;
                   border-radius: 8px; font-weight: 700; font-size: 14px;
                   cursor: pointer; text-decoration: none; }

        /* Hero */
        .hero { text-align: center; padding: 80px 24px 60px; max-width: 720px;
                margin: 0 auto; }
        .hero-eyebrow { font-size: 12px; font-weight: 700; letter-spacing: 3px;
                        color: #A8C4AE; margin-bottom: 20px; }
        .hero h1 { font-size: clamp(36px, 6vw, 60px); font-weight: 900;
                   line-height: 1.1; margin-bottom: 24px; }
        .hero h1 span { color: #C2703D; }
        .hero p { font-size: 18px; color: #A8C4AE; line-height: 1.7;
                  margin-bottom: 40px; }
        .hero-btns { display: flex; gap: 14px; justify-content: center;
                     flex-wrap: wrap; }
        .btn-primary { background: #C2703D; color: #fff; padding: 16px 32px;
                       border-radius: 10px; font-weight: 800; font-size: 16px;
                       text-decoration: none; }
        .btn-secondary { background: rgba(255,255,255,0.1); color: #fff;
                         padding: 16px 32px; border-radius: 10px;
                         font-weight: 700; font-size: 16px; text-decoration: none;
                         border: 1px solid rgba(255,255,255,0.2); }

        /* Pain points */
        .section { padding: 60px 24px; max-width: 960px; margin: 0 auto; }
        .section-label { font-size: 11px; font-weight: 700; letter-spacing: 3px;
                         color: #C2703D; margin-bottom: 16px; text-align: center; }
        .section h2 { font-size: 32px; font-weight: 900; text-align: center;
                      margin-bottom: 48px; }
        .pain-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                     gap: 20px; }
        .pain-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
                     border-radius: 12px; padding: 28px; }
        .pain-icon { font-size: 32px; margin-bottom: 14px; }
        .pain-card h3 { font-size: 17px; font-weight: 800; margin-bottom: 10px; }
        .pain-card p { font-size: 14px; color: #A8C4AE; line-height: 1.7; }
        .pain-arrow { color: #C2703D; font-weight: 700; margin: 8px 0;
                      font-size: 13px; }

        /* Features */
        .features { background: #1a3322; padding: 60px 24px; }
        .features-inner { max-width: 960px; margin: 0 auto; }
        .feat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                     gap: 20px; margin-top: 40px; }
        .feat { padding: 24px; }
        .feat-icon { width: 44px; height: 44px; background: rgba(194,112,61,0.2);
                     border-radius: 10px; display: flex; align-items: center;
                     justify-content: center; font-size: 22px; margin-bottom: 14px; }
        .feat h3 { font-size: 15px; font-weight: 800; margin-bottom: 8px; }
        .feat p { font-size: 13px; color: #A8C4AE; line-height: 1.6; }

        /* Social proof */
        .proof { background: #0a1a0f; padding: 60px 24px; text-align: center; }
        .stat-row { display: flex; justify-content: center; gap: 60px;
                    flex-wrap: wrap; margin-top: 32px; }
        .stat h3 { font-size: 42px; font-weight: 900; color: #C2703D; }
        .stat p { font-size: 13px; color: #A8C4AE; margin-top: 4px; }

        /* CTA */
        .cta-section { padding: 80px 24px; text-align: center; }
        .cta-section h2 { font-size: 32px; font-weight: 900; margin-bottom: 16px; }
        .cta-section p { color: #A8C4AE; font-size: 16px; margin-bottom: 36px; }

        /* Footer */
        footer { border-top: 1px solid rgba(255,255,255,0.1);
                 padding: 24px 40px; display: flex; justify-content: space-between;
                 align-items: center; font-size: 13px; color: #A8C4AE; flex-wrap: wrap; gap: 12px; }
      </style>
    </head>
    <body>

      <nav>
        <div class="nav-logo">FAIDA</div>
        <a class="nav-cta" href="mailto:hello@faida.co.ke">Get Started</a>
      </nav>

      <section class="hero">
        <div class="hero-eyebrow">BUILT FOR KENYAN DUKAS</div>
        <h1>Supermarkets have software.<br/><span>Now so do you.</span></h1>
        <p>Faida gives your duka the same tools big retailers use —
           stock tracking, sales reports, profit margins —
           in an app that works even when your data runs out.</p>
        <div class="hero-btns">
          <a class="btn-primary" href="mailto:hello@faida.co.ke">
            Register Your Shop
          </a>
          <a class="btn-secondary" href="#how-it-works">See How It Works</a>
        </div>
      </section>

      <section class="section">
        <div class="section-label">THE PROBLEM</div>
        <h2>Your notebook has been lying to you.</h2>
        <div class="pain-grid">
          <div class="pain-card">
            <div class="pain-icon">📒</div>
            <h3>"Cash that doesn't add up"</h3>
            <p>You counted sales all day but the till is short.
               You don't know where it went.</p>
            <div class="pain-arrow">→</div>
            <p style="color:#fff">Every sale recorded. Change calculated.
               Nothing lost.</p>
          </div>
          <div class="pain-card">
            <div class="pain-icon">📦</div>
            <h3>"Ran out and didn't know"</h3>
            <p>A customer asked for unga. Shelf was empty.
               You lost the sale and the customer.</p>
            <div class="pain-arrow">→</div>
            <p style="color:#fff">Low stock alerts before you run out.
               Fast-movers always restocked.</p>
          </div>
          <div class="pain-card">
            <div class="pain-icon">📊</div>
            <h3>"I don't know my margins"</h3>
            <p>You know what you buy. You know what you sell.
               But do you know your actual profit?</p>
            <div class="pain-arrow">→</div>
            <p style="color:#fff">Profit margin per item. Calculated automatically.
               Always visible.</p>
          </div>
        </div>
      </section>

      <div class="features" id="how-it-works">
        <div class="features-inner">
          <div class="section-label" style="text-align:center">HOW IT WORKS</div>
          <h2 style="text-align:center;font-size:32px;font-weight:900;margin-bottom:0">
            Designed for the counter, not the office.
          </h2>
          <div class="feat-grid">
            <div class="feat">
              <div class="feat-icon">🔍</div>
              <h3>Search & Sell in Seconds</h3>
              <p>Type two letters, tap the item, done.
                 New item? Quick Add it mid-sale in 3 seconds.
                 No leaving the checkout screen.</p>
            </div>
            <div class="feat">
              <div class="feat-icon">📶</div>
              <h3>Works Without Internet</h3>
              <p>Sell even when your data runs out or
                 the signal drops. Everything syncs automatically
                 the moment you reconnect.</p>
            </div>
            <div class="feat">
              <div class="feat-icon">💵</div>
              <h3>Change Calculator Built In</h3>
              <p>Customer hands you a 500 bob note.
                 Enter the amount — change shown instantly.
                 No mental arithmetic, no mistakes.</p>
            </div>
            <div class="feat">
              <div class="feat-icon">📈</div>
              <h3>Daily Sales Reports</h3>
              <p>See today's revenue, your top-selling items,
                 and your profit margins — without doing
                 a single calculation yourself.</p>
            </div>
            <div class="feat">
              <div class="feat-icon">👥</div>
              <h3>Manage Your Team</h3>
              <p>Add shopkeeper accounts. Each person logs in
                 with their own PIN. You see who sold what
                 and when.</p>
            </div>
            <div class="feat">
              <div class="feat-icon">📱</div>
              <h3>Your Phone, No Extra Hardware</h3>
              <p>No POS machine. No laptop. No receipts printer.
                 Just the phone you already have.</p>
            </div>
          </div>
        </div>
      </div>

      <div class="proof">
        <div class="section-label">BY THE NUMBERS</div>
        <h2 style="font-size:28px;font-weight:900">
          Dukas are the backbone of Kenya.
        </h2>
        <div class="stat-row">
          <div class="stat">
            <h3>80%</h3>
            <p>of Nairobi's consumer goods<br/>supplied by dukas</p>
          </div>
          <div class="stat">
            <h3>70%</h3>
            <p>of Kenya's retail sales<br/>are informal economy</p>
          </div>
          <div class="stat">
            <h3>10%</h3>
            <p>of duka owners have ever<br/>received business training</p>
          </div>
        </div>
      </div>

      <section class="cta-section">
        <h2>Ready to know your numbers?</h2>
        <p>We onboard shops personally. No credit card. No contract.
           <br/>Send us a message and we'll set you up today.</p>
        <a class="btn-primary" href="mailto:hello@faida.co.ke"
           style="display:inline-block">
          Register Your Duka →
        </a>
      </section>

      <footer>
        <div><strong>FAIDA</strong> — Duka yako, faida yako.</div>
        <div>Built for Kenyan shopkeepers &nbsp;·&nbsp;
             <a href="/admin/login" style="color:#A8C4AE">Admin</a></div>
      </footer>

    </body>
    </html>
    """