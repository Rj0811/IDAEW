CREATE TABLE IF NOT EXISTS instruments (
  instrument_token BIGINT PRIMARY KEY, exchange TEXT NOT NULL,
  tradingsymbol TEXT NOT NULL, name TEXT, instrument_type TEXT,
  expiry DATE, lot_size INTEGER, tick_size NUMERIC(18,6),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS market_bars (
  instrument_token BIGINT NOT NULL REFERENCES instruments(instrument_token),
  timeframe TEXT NOT NULL, ts TIMESTAMPTZ NOT NULL,
  open NUMERIC(18,6), high NUMERIC(18,6), low NUMERIC(18,6),
  close NUMERIC(18,6), volume BIGINT, oi BIGINT, source TEXT NOT NULL,
  PRIMARY KEY(instrument_token,timeframe,ts)
);
CREATE TABLE IF NOT EXISTS orderflow_bars (
  instrument_token BIGINT NOT NULL, ts TIMESTAMPTZ NOT NULL,
  bid_volume BIGINT, ask_volume BIGINT, delta BIGINT, cvd BIGINT,
  classification TEXT, source TEXT NOT NULL,
  PRIMARY KEY(instrument_token,ts)
);
CREATE TABLE IF NOT EXISTS futures_oi (
  instrument_token BIGINT NOT NULL, ts TIMESTAMPTZ NOT NULL,
  last_price NUMERIC(18,6), oi BIGINT, volume BIGINT, expiry DATE,
  PRIMARY KEY(instrument_token,ts)
);
CREATE TABLE IF NOT EXISTS scan_signals (
  id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT now(),
  instrument_token BIGINT, symbol TEXT NOT NULL, segment TEXT NOT NULL,
  setup TEXT, direction TEXT, score NUMERIC(6,2),
  entry_trigger NUMERIC(18,6), invalidation NUMERIC(18,6),
  target_1 NUMERIC(18,6), target_2 NUMERIC(18,6),
  evidence JSONB, data_quality JSONB, strategy_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trades (
  id BIGSERIAL PRIMARY KEY, signal_id BIGINT REFERENCES scan_signals(id),
  symbol TEXT NOT NULL, side TEXT NOT NULL, quantity INTEGER NOT NULL,
  planned_entry NUMERIC(18,6), actual_entry NUMERIC(18,6),
  stop_price NUMERIC(18,6), exit_price NUMERIC(18,6),
  costs NUMERIC(18,2), pnl NUMERIC(18,2),
  opened_at TIMESTAMPTZ, closed_at TIMESTAMPTZ, notes TEXT
);
CREATE TABLE IF NOT EXISTS risk_events (
  id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT now(),
  event_type TEXT NOT NULL, severity TEXT NOT NULL, symbol TEXT, details JSONB
);
CREATE INDEX IF NOT EXISTS idx_market_bars_ts ON market_bars(ts DESC);
CREATE INDEX IF NOT EXISTS idx_scan_signals_created ON scan_signals(created_at DESC);
