# Kafka on AWS: same workload, four setups

A vendor post recently compared self-run Kafka with Amazon MSK and reported a 59% saving. This repo recomputes the same workload with public AWS list prices. The vendor's numbers rebuild almost exactly. The saving comes from two choices, not from who runs the cluster: **one availability zone instead of three**, and **MSK brokers sized to match the self-run hardware rather than the workload**.

Write-up: [They Left Amazon MSK and Saved 59%. Read the Fine Print.](https://medium.com/@saikumaresh/they-left-amazon-msk-and-saved-59-read-the-fine-print-747821f02f65)

## Result (us-east-1, list prices checked 10 November 2026)

Workload: 5 MB/s written (13,140 GB a month), 2 TB retained, read once, replication factor 3, 730 hours a month.

| Setup | Default clients | Consumers read nearest replica |
|---|---:|---:|
| Self-run, 1 zone (clients in the same zone) | $1,016 | $1,016 |
| Self-run, 3 zones | $1,892 | $1,717 |
| MSK Standard, 3 zones, same memory (m7g.xlarge, 16 GiB) | $2,737 | $2,562 |
| MSK Standard, 3 zones, right-sized (m7g.large, 8 GiB) | $1,844 | $1,669 |
| MSK Express, 3 zones | $1,575 | $1,400 |

What this shows:
- **The vendor's figures rebuild.** One-zone self-run plus a 25% fee on compute is about $1,145 (vendor: $1,119). Memory-matched MSK Standard is $2,737 (vendor: $2,740).
- **Two choices make up the gap.** Moving self-run from one zone to three adds $876 a month. Memory-matched MSK brokers cost $893 a month more than right-sized ones.
- **With equal zones, self-run saves 31% against memory-matched MSK**, roughly ties right-sized MSK Standard, and costs about 20% more than MSK Express.
- **Replication across zones is the big hidden line.** A three-zone self-run cluster pays $526 a month to copy replicas between zones, about the same as its brokers. MSK does not charge for replication between brokers.
- **Express is the cheapest three-zone option at this size**, because it bills storage on data stored rather than on every replica. Above roughly 10 to 20 MB/s, right-sized Standard becomes cheaper, because Express charges per GB written.
- **Rack awareness is free money.** Letting consumers read from a replica in their own zone removes $175 a month in every three-zone setup.
- **None of this includes people.** The self-run rows exclude the engineers who replace brokers, rebalance partitions and answer pages.

At higher traffic the cross-zone lines grow linearly while the brokers do not. With brokers held constant, at 50 MB/s the three-zone self-run cluster costs about twice right-sized MSK Standard (`python3 model.py --mbps 50`).

Full line items: [results.txt](results.txt).

## Run it

```
python3 model.py                                   # default workload
python3 model.py --mbps 20 --retained-tb 10 --reads 3
python3 model.py --json
python3 -m pytest -q                               # 8 checks, including that it rebuilds the vendor totals
```

Prices and their sources live in [prices.json](prices.json). Change them for your region or discounts.

## Assumptions

- Six brokers for self-run and MSK Standard (the broker count in the original comparison); three for MSK Express (its minimum, one per zone).
- Broker size: self-run uses r8g.large (2 vCPU, 16 GiB). MSK Standard is priced both memory-matched (kafka.m7g.xlarge, 16 GiB, as in the original comparison) and right-sized for 5 MB/s (kafka.m7g.large, 8 GiB). Broker prices come from the AWS Price List API offer file for MSK in us-east-1 (kafka.m7g.large $0.204/h, kafka.m7g.xlarge $0.408/h).
- Standard storage is billed on every replica (each broker's disk). Express storage is billed on data stored, as in AWS's own pricing example.
- Clients sit evenly across three zones, so two times in three a producer or consumer talks to a leader in another zone. Cross-zone traffic costs $0.01/GB on each side.
- In the one-zone row, clients are in the same zone, as in the original comparison. A real zone outage takes that cluster down.
- No reserved instances, savings plans, tiered storage or internet egress. A managed vendor's fee (for example 25% of compute) is not included.

This is a personal project for learning. It is not affiliated with AWS or any Kafka vendor, and it is not pricing advice. Check current prices before deciding.

## Sources

- Artie, "We Left MSK, Built Our Own Kafka, and Now Sell It at EC2 + 25%", 3 November 2026: https://www.artie.com/blogs/we-left-msk-built-our-own-kafka
- Amazon MSK pricing: https://aws.amazon.com/msk/pricing/ and the AWS Price List API offer file: https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonMSK/current/us-east-1/index.json
- AWS, cross-zone transfer billed on both sides: https://aws.amazon.com/blogs/architecture/exploring-data-transfer-costs-for-aws-managed-databases
- AWS, rack awareness for MSK consumers: https://aws.amazon.com/blogs/big-data/reduce-network-traffic-costs-of-your-amazon-msk-consumers-with-rack-awareness
- MSK Express intelligent rebalancing (Nov 2025) and on existing clusters (June 2026): https://aws.amazon.com/about-aws/whats-new/2025/11/aws-msk-express-brokers-support-intelligent-rebalancing , https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-msk-express-intelligent/
- EC2 r8g.large on-demand price: https://instances.vantage.sh/aws/ec2/r8g.large

## Licence

MIT
