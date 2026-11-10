"""Kafka on AWS: same workload, four setups.

Recomputes one workload with public AWS list prices so the differences
come from architecture, not from who runs the cluster.
Run: python3 model.py            (default workload)
     python3 model.py --mbps 20 --retained-tb 10 --reads 3
"""
import argparse, json, pathlib

P = {k: v["value"] for k, v in json.loads(
    (pathlib.Path(__file__).parent / "prices.json").read_text()).items() if not k.startswith("_")}
H = 730  # hours per month


def workload(mbps, retained_tb, reads, rf=3):
    ingest_gb = mbps * 3600 * H / 1000          # GB written per month (decimal)
    return dict(mbps=mbps, ingest_gb=ingest_gb, read_gb=ingest_gb * reads,
                logical_gb=retained_tb * 1000, replicated_gb=retained_tb * 1000 * rf, rf=rf)


def client_cross_az(w, zones_clients, rack_aware):
    """Clients spread evenly over 3 zones talk to leaders spread over the broker zones.
    Each GB that crosses a zone is billed on both sides."""
    xaz = 2 * P["cross_az_gb_each_side"]
    if zones_clients == 1:
        return 0.0, 0.0
    share = 2 / 3                               # leader is in another zone 2 times in 3
    produce = w["ingest_gb"] * share * xaz
    consume = 0.0 if rack_aware else w["read_gb"] * share * xaz
    return produce, consume


def self_run(w, zones, brokers=6, rack_aware=False):
    items = {}
    items["brokers (EC2 r8g.large)"] = brokers * P["ec2_r8g_large_hour"] * H
    items["disks (gp3, all replicas)"] = w["replicated_gb"] * P["ebs_gp3_gb_month"]
    items["load balancer + IPv4"] = P["nlb_month"] + P["public_ipv4_month"]
    xaz = 2 * P["cross_az_gb_each_side"]
    items["replication across zones"] = 0.0 if zones == 1 else w["ingest_gb"] * (w["rf"] - 1) * xaz
    p, c = client_cross_az(w, 1 if zones == 1 else 3, rack_aware)
    items["producers across zones"], items["consumers across zones"] = p, c
    return items


def msk_standard(w, brokers=6, rack_aware=False):
    items = {}
    items["brokers (kafka.m7g.large)"] = brokers * P["msk_standard_m7g_large_hour"] * H
    items["storage (all replicas)"] = w["replicated_gb"] * P["msk_standard_storage_gb_month"]
    items["replication across zones"] = 0.0     # not charged by MSK
    p, c = client_cross_az(w, 3, rack_aware)
    items["producers across zones"], items["consumers across zones"] = p, c
    return items


def msk_express(w, brokers=3, rack_aware=False):
    items = {}
    items["brokers (express.m7g.large)"] = brokers * P["msk_express_m7g_large_hour"] * H
    items["storage (data stored)"] = w["logical_gb"] * P["msk_express_storage_gb_month"]
    items["data in"] = w["ingest_gb"] * P["msk_express_data_in_gb"]
    items["replication across zones"] = 0.0
    p, c = client_cross_az(w, 3, rack_aware)
    items["producers across zones"], items["consumers across zones"] = p, c
    return items


def scenarios(w, rack_aware=False):
    return {
        "Self-run, 1 zone (clients in same zone)": self_run(w, 1),
        "Self-run, 3 zones": self_run(w, 3, rack_aware=rack_aware),
        "MSK Standard, 3 zones": msk_standard(w, rack_aware=rack_aware),
        "MSK Express, 3 zones": msk_express(w, rack_aware=rack_aware),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mbps", type=float, default=5)
    ap.add_argument("--retained-tb", type=float, default=2)
    ap.add_argument("--reads", type=float, default=1)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    w = workload(a.mbps, a.retained_tb, a.reads)
    out = {}
    for ra in (False, True):
        out["rack_aware" if ra else "default"] = {
            k: {"items": {i: round(v, 2) for i, v in s.items()}, "total": round(sum(s.values()), 2)}
            for k, s in scenarios(w, ra).items()}
    if a.json:
        print(json.dumps({"workload": w, "results": out}, indent=2)); return
    print(f"Workload: {a.mbps} MB/s in ({w['ingest_gb']:,.0f} GB/month), {a.retained_tb} TB retained, "
          f"read {a.reads}x, replication factor {w['rf']}, us-east-1, {H} h/month\n")
    for mode, res in out.items():
        print(f"== {'consumers read from nearest replica (rack awareness)' if mode=='rack_aware' else 'default client settings'} ==")
        for name, r in res.items():
            print(f"{name:42s} ${r['total']:>9,.2f}")
        print()
    print("Line items (default settings):")
    for name, r in out["default"].items():
        print(f"\n{name}")
        for i, v in r["items"].items():
            print(f"  {i:34s} ${v:>9,.2f}")


if __name__ == "__main__":
    main()
