---
title: DBWarden Test Harness
description: Black-box release validation for DBWarden, real database backends, and plugins.
---

<p align="center">
  <img src="https://raw.githubusercontent.com/dbwarden-org/dbwarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
  <strong style="font-size: 2.5em;">DBWarden Test Harness</strong>
</p>
<p align="center">
    <em>Release confidence through real databases and public interfaces.</em>
</p>
<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white&style=for-the-badge" alt="Python">
  </a>
  <a href="https://github.com/dbwarden-org/dbwarden-harness/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/dbwarden-org/dbwarden-harness/.github/workflows/pr-gate.yml?branch=main&label=CI&logo=github&style=for-the-badge" alt="CI">
  </a>
  <a href="https://github.com/dbwarden-org/dbwarden-harness">
    <img src="https://img.shields.io/badge/Testing-Black--box-10AC84?style=for-the-badge" alt="Black box testing">
  </a>
  <a href="https://www.docker.com/">
    <img src="https://img.shields.io/badge/Docker-Testcontainers-2496ED?logo=docker&logoColor=white&style=for-the-badge" alt="Docker Testcontainers">
  </a>
</p>

<p align="center">
  <strong><a href="https://harness.dbwarden.org/">Documentation</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/dbwarden-org/dbwarden-harness">Source Code</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/dbwarden-org/dbwarden">DBWarden</a></strong>
</p>

The DBWarden Test Harness is the release boundary between DBWarden development
and DBWarden consumption.

It installs DBWarden as an external package, invokes public commands, runs
against real disposable databases, and checks the resulting state. The harness
is intentionally separate from the DBWarden source repository because source
tests and consumer tests answer different questions.

## Start here

- Read [Why a Harness?](why-a-harness.md) for the design rationale.
- Follow [Setup](getting-started/setup.md) to install the locked environment.
- Use [Running Tests](getting-started/running-tests.md) for local and CI commands.
- Read [Correctness](correctness/index.md) to understand what a passing test means.
- Check [Compatibility Findings](operations/compatibility.md) before interpreting an experimental failure.

## What is validated

The harness validates distribution installation, public CLI behavior, migration
application, rollback, reverse engineering, semantic convergence, provider
isolation, plugin discovery, adoption flows, offline state, and performance.

The primary unit of confidence is not a generated SQL string. It is a complete
consumer flow that produces the expected live database state and can explain
why it passed or failed.

## Repository

The source repository is available at
[dbwarden-org/dbwarden-harness](https://github.com/dbwarden-org/dbwarden-harness).

The product being tested is documented at
[dbwarden-org/dbwarden](https://github.com/dbwarden-org/dbwarden).

For machine-readable documentation, use
