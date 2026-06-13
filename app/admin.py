"""引导脚本：创建 org 与 API Key（解决首个凭据的鸡生蛋问题）。

用法：
    python -m app.admin create-org --name "Acme"
输出的明文 API Key 仅此一次可见，请妥善保存。
"""

from __future__ import annotations

import argparse
import asyncio

from app.auth.security import generate_api_key
from app.db.models import ApiKey, Org
from app.db.session import get_sessionmaker


async def create_org(name: str, key_name: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        org = Org(name=name)
        session.add(org)
        await session.flush()

        plaintext, prefix, hashed = generate_api_key()
        session.add(
            ApiKey(org_id=org.id, name=key_name, prefix=prefix, hashed_key=hashed)
        )
        await session.commit()

        print(f"org_id   = {org.id}")
        print(f"api_key  = {plaintext}   # 仅此一次可见，请保存")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.admin")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create-org", help="创建 org 并生成 API Key")
    p.add_argument("--name", required=True)
    p.add_argument("--key-name", default="default")

    args = parser.parse_args()
    if args.cmd == "create-org":
        asyncio.run(create_org(args.name, args.key_name))


if __name__ == "__main__":
    main()
