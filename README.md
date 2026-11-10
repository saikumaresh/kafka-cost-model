# Kafka on AWS: same workload, four setups

A vendor post recently compared self-run Kafka with Amazon MSK and reported a 59% saving. The headline number compares a cluster in **one availability zone** with MSK running across **three**. This repo recomputes the same workload with public AWS list prices, so the difference you see comes from the architecture, not from who runs the cluster.

Write-up: _link added after publishing_

## Result (us-east-1, list prices checked 10 November 2026)

Workload: 5 MB/s written (13,140 GB a month), 2 TB retained, read once, replication factor 3, 730 hours a month.

| Setup | Default clients | Consumers read nearest replica |
|---|---:|---:|
| Self-run, 1 zone (clients in the same zone) | $1,016 | $1,016 |
| Self-run, 3 zones | $1,892 | $1,717 |
| MSK Standard, 3 zones | $1,844 | $1,669 |
| MSK Express, 3 zones | $1,575 | $1,400 |

What this shows:
- **One zone vs three is most of the gap.** The one-zone self-run cluster is 45% cheaper than MSK Standard on infrastructure.
- **Match the resilience and the saving disappears.** Spread the self-run cluster over three zones and it costs slightly more than MSK Standard, because every replica copy crosses a zone and is billed on both sides ($526 a month here, about the same as the brokers). MSK does not charge for replication between brokers.
- **Express is the cheapest three-zone option at this size**, even at twice the hourly broker price, because it bills storage on data stored rather than on every replica.
- **Rack awareness is free money.** Letting consumers read from a replica in their own zone removes $175 a month in every three-zone setup.
- **None of this includes people.** The self-run rows exclude the engineers who replace brokers, rebalance partitions and answer pages. Add that to compare honestly.

At higher traffic the cross-zone line grows linearly while the brokers do not, so the gap widens. With brokers held constant, at 50 MB/s the three-zone self-run cluster costs about twice MSK Standard (`python3 model.py --mbps 50`).

Full line items: [results.txt](results.txt).

## Run it

```
python3 model.py                                   # default workload
python3 model.py --mbps 20 --retained-tb 10 --reads 3
python3 model.py --json
python3 -m pytest -q                               # 6 checks on the pricing rules
```

Prices and their sources live in [prices.json](prices.json). Change them for your region or discounts.

## Assumptions

- Six brokers for self-run and MSK Standard (the broker count in the original comparison); three for MSK Express (its minimum, one per zone). The workload is small enough for both.
- Standard storage is billed on every replica (each broker's disk). Express storage is billed on data stored, as in AWS's own pricing example.
- Clients sit evenly across three zones, so two times in three a producer or consumer talks to a leader in another zone. Cross-zone traffic costs $0.01/GB on each side.
- In the one-zone row, clients are in the same zone, as in the original comparison. A real zone outage takes that cluster down.
- No reserved instances, savings plans, tiered storage or internet egress. A managed vendor's fee (for example 25% of compute) is not included.
- Vendor figures from the original post could not be fully reproduced from public prices, because not all of its inputs are published.

This is a personal project for learning. It is not affiliated with AWS or any Kafka vendor, and it is not pricing advice. Check current prices before deciding.

## Sources

- Artie, "We Left MSK, Built Our Own Kafka, and Now Sell It at EC2 + 25%", 3 November 2026: https://www.artie.com/blogs/we-left-msk-built-our-own-kafka
- Amazon MSK pricing: https://aws.amazon.com/msk/pricing/
- AWS, cross-zone transfer billed on both sides: https://aws.amazon.com/blogs/architecture/exploring-data-transfer-costs-for-aws-managed-databases
- AWS, rack awareness for MSK consumers: https://aws.amazon.com/blogs/big-data/reduce-network-traffic-costs-of-your-amazon-msk-consumers-with-rack-awareness
- MSK Express intelligent rebalancing (Nov 2025) and on existing clusters (June 2026): https://aws.amazon.com/about-aws/whats-new/2025/11/aws-msk-express-brokers-support-intelligent-rebalancing , https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-msk-express-intelligent/
- EC2 r8g.large on-demand price: https://instances.vantage.sh/aws/ec2/r8g.large

## Licence

MIT
