import { useState, useEffect, useMemo } from "react";
import { Gauge, Fuel, Settings2, RefreshCw, AlertCircle } from "lucide-react";

const SUPABASE_URL = "https://zjrasfqhrbrmhynbgkbu.supabase.co";
// Use the PUBLISHABLE key here, never the secret key, since this runs in the browser.
const SUPABASE_ANON_KEY = "sb_publishable_XNSfnbje63QJvXkdBk5aMw_Mv2gVt76";

export default function CarListings() {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCars = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${SUPABASE_URL}/rest/v1/cars?select=*&order=scraped_at.desc`,
        {
          headers: {
            apikey: SUPABASE_ANON_KEY,
            Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          },
        }
      );
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      setCars(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCars();
  }, []);

  const maxMileage = useMemo(() => {
    if (cars.length === 0) return 1;
    return Math.max(...cars.map((c) => c.mileage_km || 0), 1);
  }, [cars]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#1c1a18",
        color: "#f0ebe2",
        fontFamily:
          "'Oswald', 'Arial Narrow', sans-serif",
        padding: "32px 24px 64px",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        .car-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
        }
        .car-card {
          background: #25221f;
          border: 1px solid #3a352f;
          border-radius: 4px;
          padding: 18px;
          transition: border-color 0.15s ease, transform 0.15s ease;
        }
        .car-card:hover {
          border-color: #d97f3c;
          transform: translateY(-2px);
        }
        .mono { font-family: 'JetBrains Mono', monospace; }
        .stat-row {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #9d958a;
          font-size: 13px;
        }
        .refresh-btn {
          background: #d97f3c;
          color: #1c1a18;
          border: none;
          border-radius: 3px;
          padding: 8px 16px;
          font-family: 'Oswald', sans-serif;
          font-weight: 600;
          font-size: 13px;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: background 0.15s ease;
        }
        .refresh-btn:hover { background: #e8924f; }
        .refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .refresh-btn:focus-visible {
          outline: 2px solid #f0ebe2;
          outline-offset: 2px;
        }
        @media (prefers-reduced-motion: reduce) {
          .car-card { transition: none; }
        }
      `}</style>

      <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            marginBottom: "28px",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <div
              className="mono"
              style={{
                color: "#d97f3c",
                fontSize: "12px",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                marginBottom: "4px",
              }}
            >
              Stocklist
            </div>
            <h1
              style={{
                fontSize: "32px",
                fontWeight: 700,
                margin: 0,
                letterSpacing: "-0.01em",
              }}
            >
              Scraped Inventory
            </h1>
          </div>
          <button className="refresh-btn" onClick={fetchCars} disabled={loading}>
            <RefreshCw size={14} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            {loading ? "Loading" : "Refresh"}
          </button>
        </div>

        <style>{`
          @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        `}</style>

        {error && (
          <div
            style={{
              background: "#3a221c",
              border: "1px solid #d9543c",
              borderRadius: "4px",
              padding: "14px 16px",
              marginBottom: "20px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              color: "#f0b8a8",
            }}
          >
            <AlertCircle size={18} />
            <span>Couldn't load listings: {error}. Check your Supabase URL and key, then refresh.</span>
          </div>
        )}

        {!loading && !error && cars.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "60px 20px",
              color: "#7a7165",
            }}
          >
            No listings yet. Run the scraper, then refresh this page.
          </div>
        )}

        <div className="car-grid">
          {cars.map((car) => {
            const mileagePct = Math.min(
              100,
              ((car.mileage_km || 0) / maxMileage) * 100
            );
            const price = car.price_nzd ?? car.price_jpy;
            const currency = car.price_nzd != null ? "NZD" : "JPY";
            return (
              <div className="car-card" key={car.id}>
                <div
                  style={{
                    fontSize: "11px",
                    color: "#7a7165",
                    marginBottom: "4px",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  {car.source}
                </div>
                <h3
                  style={{
                    margin: "0 0 10px",
                    fontSize: "16px",
                    fontWeight: 600,
                    lineHeight: 1.25,
                    minHeight: "40px",
                  }}
                >
                  {car.title}
                </h3>

                <div
                  className="mono"
                  style={{
                    fontSize: "24px",
                    fontWeight: 600,
                    color: "#d97f3c",
                    marginBottom: "12px",
                  }}
                >
                  {price != null
                    ? `${price.toLocaleString()} ${currency}`
                    : "Price on request"}
                </div>

                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div className="stat-row">
                    <Gauge size={14} />
                    <span className="mono">
                      {car.mileage_km != null
                        ? `${car.mileage_km.toLocaleString()} km`
                        : " Ekm"}
                    </span>
                  </div>
                  <div
                    style={{
                      height: "3px",
                      background: "#3a352f",
                      borderRadius: "2px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${mileagePct}%`,
                        background: "#5b7a8c",
                      }}
                    />
                  </div>

                  <div style={{ display: "flex", gap: "16px", marginTop: "4px" }}>
                    <div className="stat-row">
                      <Fuel size={14} />
                      <span className="mono">
                        {car.engine_cc ? `${car.engine_cc}cc` : " E}
                      </span>
                    </div>
                    <div className="stat-row">
                      <Settings2 size={14} />
                      <span className="mono">{car.transmission || " E}</span>
                    </div>
                  </div>
                </div>

                <a
                  href={car.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "block",
                    marginTop: "14px",
                    fontSize: "12px",
                    color: "#9d958a",
                    textDecoration: "none",
                    borderTop: "1px solid #3a352f",
                    paddingTop: "10px",
                  }}
                >
                  View listing ↁE                </a>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
