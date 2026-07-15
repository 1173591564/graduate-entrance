from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from graduate_entrance.api.routes.syllabus import get_syllabus_response
from graduate_entrance.main import app
from graduate_entrance.schemas.syllabus import SyllabusTreeResponse


async def fake_syllabus_tree() -> SyllabusTreeResponse:
    return SyllabusTreeResponse.model_validate(
        {
            "source_row_count": 1,
            "knowledge_point_count": 1,
            "exam_blueprint_count": 0,
            "versions": [
                {
                    "id": "version-id",
                    "source_name": "数学一考纲.csv",
                    "source_checksum": "checksum",
                    "row_count": 1,
                    "imported_at": "2026-07-15T00:00:00Z",
                }
            ],
            "subjects": [
                {
                    "id": "subject-id",
                    "code": "数学一",
                    "name": "数学一",
                    "order": 1,
                    "source_row_count": 1,
                    "knowledge_point_count": 1,
                    "exam_blueprints": [],
                    "modules": [
                        {
                            "id": "module-id",
                            "name": "高等数学",
                            "order": 1,
                            "chapters": [
                                {
                                    "id": "chapter-id",
                                    "name": "函数极限连续",
                                    "order": 1,
                                    "sections": [
                                        {
                                            "id": "section-id",
                                            "name": "函数",
                                            "order": 1,
                                            "knowledge_points": [
                                                {
                                                    "id": "kp-id",
                                                    "name": "函数的概念",
                                                    "requirement_raw": "理解",
                                                    "requirement_level": "understanding",
                                                    "requirement_actions": [],
                                                    "common_exam_style": "",
                                                    "note": "",
                                                    "order": 1,
                                                }
                                            ],
                                        }
                                    ],
                                    "knowledge_points": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_syllabus_response] = fake_syllabus_tree
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer local-development-only"},
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_read_syllabus_returns_tree(client: AsyncClient) -> None:
    response = await client.get("/api/syllabus")

    assert response.status_code == 200
    assert (
        response.json()["subjects"][0]["modules"][0]["chapters"][0]["sections"][0][
            "knowledge_points"
        ][0]["name"]
        == "函数的概念"
    )
