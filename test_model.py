import model

W = model.workload(5, 2, 1)

def test_ingest():
    assert round(W["ingest_gb"]) == 13140

def test_msk_does_not_charge_replication():
    assert model.msk_standard(W)["replication across zones"] == 0
    assert model.msk_express(W)["replication across zones"] == 0

def test_three_zone_self_run_pays_two_copies_both_sides():
    assert round(model.self_run(W, 3)["replication across zones"], 2) == round(13140 * 2 * 0.02, 2)

def test_one_zone_has_no_cross_zone_cost():
    s = model.self_run(W, 1)
    assert s["replication across zones"] == s["producers across zones"] == s["consumers across zones"] == 0

def test_rack_awareness_only_removes_consumer_traffic():
    a, b = model.msk_standard(W), model.msk_standard(W, rack_aware=True)
    assert b["consumers across zones"] == 0 and a["producers across zones"] == b["producers across zones"]

def test_headline_ordering():
    t = {k: sum(v.values()) for k, v in model.scenarios(W).items()}
    assert t["Self-run, 1 zone (clients in same zone)"] < t["MSK Express, 3 zones"] < t["MSK Standard, 3 zones"] < t["Self-run, 3 zones"]

def test_memory_matched_msk_rebuilds_the_vendor_figure():
    total = sum(model.msk_standard(W, size="xlarge").values())
    assert abs(total - 2740) < 10        # vendor post: $2,740

def test_self_run_one_zone_plus_fee_close_to_vendor():
    s = model.self_run(W, 1)
    total = sum(s.values()) + 0.25 * s["brokers (EC2 r8g.large)"]
    assert abs(total - 1119) < 40        # vendor post: $1,119
