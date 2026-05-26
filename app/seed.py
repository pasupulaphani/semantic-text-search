import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Client, Document

logger = logging.getLogger(__name__)
SEED_CLIENTS: list[dict] = [
    {
        "first_name": "Alice",
        "last_name": "Thornton",
        "email": "alice.thornton@demo.com",
        "description": "High-net-worth individual, onboarded Q1 2024. Primary residence UK.",
        "social_links": [
            "https://linkedin.com/in/alicethornton",
            "https://twitter.com/alicethornton",
        ],
        "documents": [
            {
                "title": "Utility Bill – March 2024",
                "content": "British Gas. Account holder: Alice Thornton. Address: 14 Kensington Gardens, London W8 4PT. Account number: BG-9876543. Period: 01 Mar – 31 Mar 2024. Amount due: £142.50. This document confirms the residential address of the account holder and serves as proof of address.",
                "doc_type": "address_proof",
            },
            {
                "title": "UK Passport – Alice Thornton",
                "content": "Passport number: 987654321. Nationality: British. Date of birth: 15 June 1985. Place of birth: London, UK. Issue date: 10 January 2020. Expiry date: 09 January 2030. Issued by: Her Majesty's Passport Office. This document is a government-issued photo identity document.",
                "doc_type": "id_document",
            },
            {
                "title": "Barclays Bank Statement – February 2024",
                "content": "Barclays Bank PLC. Account holder: Alice Thornton. Sort code: 20-00-00. Account number: 12345678. Statement period: 01 Feb – 29 Feb 2024. Opening balance: £24,500.00. Closing balance: £31,200.00. Transactions include salary credit of £8,500, rent payment of £2,200, investment transfer of £5,000 to ISA account. This statement demonstrates source of funds and financial standing.",
                "doc_type": "bank_statement",
            },
            {
                "title": "Employment Contract – Thornton Capital Ltd",
                "content": "This employment contract is between Thornton Capital Ltd (the Employer) and Alice Thornton (the Employee). Position: Chief Investment Officer. Start date: 1 March 2019. Annual salary: £185,000 plus performance bonus. Place of work: 14 Kensington Gardens, London. This document confirms employment status and income source.",
                "doc_type": "employment_proof",
            },
        ],
    },
    {
        "first_name": "Marcus",
        "last_name": "Osei",
        "email": "marcus.osei@demo.com",
        "description": "Entrepreneur and angel investor. Dual citizen UK/Ghana. Onboarded Q2 2024.",
        "social_links": ["https://linkedin.com/in/marcosei"],
        "documents": [
            {
                "title": "Council Tax Bill – April 2024",
                "content": "London Borough of Hackney. Liable party: Marcus Osei. Property address: 7 Shoreditch High Street, London E1 6JJ. Council tax band: D. Annual charge: £1,842.00. Reference: HCK-2024-00441. This council tax bill confirms the residential address of the liable party and is accepted as proof of address for KYC purposes.",
                "doc_type": "address_proof",
            },
            {
                "title": "Ghana National ID Card",
                "content": "Ghana Card. National Identification Authority. Full name: Marcus Kwame Osei. ID number: GHA-000123456-0. Date of birth: 22 September 1980. Gender: Male. Issue date: 15 August 2022. Expiry: 14 August 2032. This is a government-issued national identity document.",
                "doc_type": "id_document",
            },
            {
                "title": "Osei Ventures Ltd – Audited Accounts 2023",
                "content": "Osei Ventures Ltd. Company number: 09876543. Registered office: 7 Shoreditch High Street, London E1 6JJ. Turnover: £2,340,000. Net profit: £480,000. Director: Marcus Kwame Osei. Auditor: Grant Thornton LLP. These audited accounts demonstrate the source of wealth and business income for the director and beneficial owner.",
                "doc_type": "source_of_wealth",
            },
            {
                "title": "HMRC Self-Assessment Tax Return 2022/23",
                "content": "HM Revenue & Customs. Taxpayer: Marcus Kwame Osei. UTR: 1234567890. Tax year: 6 April 2022 to 5 April 2023. Total income: £310,000. Tax paid: £124,000. Income sources: dividends from Osei Ventures Ltd, rental income, capital gains from share disposal. This tax return confirms declared income and tax compliance.",
                "doc_type": "tax_document",
            },
        ],
    },
    {
        "first_name": "Priya",
        "last_name": "Sharma",
        "email": "priya.sharma@demo.com",
        "description": "Tech executive, recently relocated from Singapore. Onboarded Q3 2024.",
        "social_links": [
            "https://linkedin.com/in/priyasharma",
            "https://github.com/priyasharma",
        ],
        "documents": [
            {
                "title": "Electricity Bill – May 2024",
                "content": "EDF Energy. Customer: Priya Sharma. Supply address: 22 Canary Wharf, London E14 5AB. Account number: EDF-44556677. Meter reading: 12345 kWh. Bill date: 31 May 2024. Amount: £98.40. This electricity bill confirms the residential address of the customer and is valid as proof of address.",
                "doc_type": "address_proof",
            },
            {
                "title": "Singapore Passport – Priya Sharma",
                "content": "Republic of Singapore. Passport number: S1234567A. Name: Priya Sharma. Date of birth: 3 March 1990. Sex: F. Nationality: Singapore Citizen. Date of issue: 20 May 2021. Date of expiry: 19 May 2031. This is a valid travel document and government-issued photo ID.",
                "doc_type": "id_document",
            },
            {
                "title": "Offer Letter – TechCorp UK Ltd",
                "content": "TechCorp UK Ltd. Dear Priya Sharma, We are pleased to offer you the position of VP Engineering. Start date: 1 June 2024. Base salary: £220,000 per annum. Bonus: up to 30% of base salary. Stock options: 50,000 units vesting over 4 years. Reporting to: Chief Technology Officer. This offer letter confirms employment and income for the purposes of KYC verification.",
                "doc_type": "employment_proof",
            },
            {
                "title": "DBS Bank Statement – April 2024",
                "content": "DBS Bank Singapore. Account holder: Priya Sharma. Account number: 0123456789. Currency: SGD. Statement period: 1 April – 30 April 2024. Opening balance: SGD 145,000. Closing balance: SGD 162,500. Credits include salary SGD 18,000 and investment returns SGD 4,200. This bank statement demonstrates financial standing and source of funds.",
                "doc_type": "bank_statement",
            },
            {
                "title": "UK Biometric Residence Permit",
                "content": "UK Visas and Immigration. Biometric Residence Permit. Holder: Priya Sharma. BRP number: ZU1234567. Date of birth: 03/03/1990. Nationality: Singaporean. Leave to remain: Skilled Worker. Valid from: 01/06/2024. Valid to: 01/06/2029. This BRP confirms the right to work and reside in the United Kingdom.",
                "doc_type": "immigration_document",
            },
        ],
    },
]


async def seed_database() -> None:
    async with AsyncSessionLocal() as session:
        created_clients = 0
        created_docs = 0
        for client_data in SEED_CLIENTS:
            client = await _get_or_create_client(session, client_data)
            if client is None:
                continue
            created_clients += 1
            for doc_data in client_data["documents"]:
                doc = Document(
                    id=uuid.uuid4(),
                    client_id=client.id,
                    title=doc_data["title"],
                    content=doc_data["content"],
                    doc_type=doc_data.get("doc_type"),
                )
                session.add(doc)
                created_docs += 1
                _schedule_embedding(doc.id, doc_data["content"])
        await session.commit()
        if created_clients:
            logger.info(
                "Seed complete: %d clients, %d documents inserted.",
                created_clients,
                created_docs,
            )
        else:
            logger.info("Seed skipped — data already present.")


async def _get_or_create_client(session: AsyncSession, data: dict) -> Client | None:
    result = await session.execute(select(Client).where(Client.email == data["email"]))
    if result.scalar_one_or_none():
        return None
    client = Client(
        id=uuid.uuid4(),
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        description=data.get("description"),
        social_links=data.get("social_links"),
    )
    session.add(client)
    await session.flush()
    return client


def _schedule_embedding(document_id: uuid.UUID, content: str) -> None:
    import asyncio
    from app.routers.documents import _generate_and_save_embedding

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_generate_and_save_embedding(document_id, content))
    except Exception as exc:
        logger.debug("Could not schedule embedding for %s: %s", document_id, exc)
