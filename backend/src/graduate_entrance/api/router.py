from fastapi import APIRouter, Depends

from graduate_entrance.api.routes.calendar import router as calendar_router
from graduate_entrance.api.routes.chat import router as chat_router
from graduate_entrance.api.routes.daily import router as daily_router
from graduate_entrance.api.routes.essay import router as essay_router
from graduate_entrance.api.routes.health import public_router as public_health_router
from graduate_entrance.api.routes.health import router as protected_health_router
from graduate_entrance.api.routes.mastery import router as mastery_router
from graduate_entrance.api.routes.papers import router as papers_router
from graduate_entrance.api.routes.plan import router as plan_router
from graduate_entrance.api.routes.planning import router as planning_router
from graduate_entrance.api.routes.problems import router as problems_router
from graduate_entrance.api.routes.profile import router as profile_router
from graduate_entrance.api.routes.recitation import router as recitation_router
from graduate_entrance.api.routes.retro import router as retro_router
from graduate_entrance.api.routes.stats import router as stats_router
from graduate_entrance.api.routes.syllabus import router as syllabus_router
from graduate_entrance.api.routes.vocab import router as vocab_router
from graduate_entrance.core.auth import require_api_token

public_api_router = APIRouter()
public_api_router.include_router(public_health_router)

protected_api_router = APIRouter(dependencies=[Depends(require_api_token)])
protected_api_router.include_router(protected_health_router)
protected_api_router.include_router(syllabus_router)
protected_api_router.include_router(planning_router)
protected_api_router.include_router(plan_router)
protected_api_router.include_router(calendar_router)
protected_api_router.include_router(daily_router)
protected_api_router.include_router(problems_router)
protected_api_router.include_router(stats_router)
protected_api_router.include_router(essay_router)
protected_api_router.include_router(profile_router)
protected_api_router.include_router(mastery_router)
protected_api_router.include_router(papers_router)
protected_api_router.include_router(retro_router)
protected_api_router.include_router(vocab_router)
protected_api_router.include_router(recitation_router)
protected_api_router.include_router(chat_router)
