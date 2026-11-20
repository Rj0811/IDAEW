from src.iadew.scanner import run_scan

if __name__ == "__main__":
    result = run_scan()
    if result.empty:
        print("No candidates. Check market session, data access and configured filters.")
    else:
        print(result[["symbol", "segment", "price", "rvol", "day_return_pct", "score", "bias"]].to_string(index=False))
