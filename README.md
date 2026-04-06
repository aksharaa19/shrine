\# Shrine - Comment Stream Sentinel



\## Overview

Shrine is a production-ready predictive toxicity detection system for YouTube comment sections and live streams. It uses machine learning (Toxic-BERT) to analyze sentiment, detect coordinated attacks, and provide real-time alerts for PR firms managing brand reputation.



\## Features

\- YouTube video comment analysis with toxicity scoring

\- Real-time live stream chat monitoring

\- Sliding window sentiment analysis with velocity and acceleration metrics

\- Coordinated attack detection (hate raids, duplicate flooding)

\- Predictive alerts 1-2 minutes before toxicity escalation

\- Intervention recommendations with priority levels

\- Post-mortem report generation (JSON/CSV export)

\- User authentication (traditional + Google OAuth2)

\- PostgreSQL database for persistent storage

\- Prometheus metrics and Grafana dashboards

\- Docker containerization and Kubernetes support

\- CI/CD pipeline with GitHub Actions

\- Infrastructure as Code with Terraform



\## Technology Stack

| Category | Technologies |

|----------|--------------|

| Frontend | HTML5, CSS3, JavaScript, Chart.js |

| Backend | Python 3.9, Flask, Gunicorn |

| Database | PostgreSQL (Cloud SQL) |

| ML/NLP | Toxic-BERT, VADER, Transformers |

| Auth | JWT, OAuth2, Google Sign-In |

| Monitoring | Prometheus, Grafana |

| Logging | JSON logging, Cloud Logging |

| Container | Docker, Kubernetes |

| CI/CD | GitHub Actions |

| IaC | Terraform |

| Cloud | Google Cloud Platform (App Engine, Cloud SQL, Cloud Storage) |



\## Prerequisites

\- Python 3.9+

\- Docker and Docker Compose

\- Google Cloud Platform account

\- YouTube Data API v3 enabled

\- Google OAuth2 credentials



\## Installation



\### 1. Clone the repository

```bash

git clone https://github.com/your-username/shrine.git

cd shrine

