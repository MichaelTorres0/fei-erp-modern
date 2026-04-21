from rest_framework.routers import DefaultRouter

from .views import PickTicketViewSet

router = DefaultRouter()
router.register("", PickTicketViewSet, basename="pick-ticket")

urlpatterns = router.urls
