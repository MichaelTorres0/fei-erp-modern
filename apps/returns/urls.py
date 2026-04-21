from rest_framework.routers import DefaultRouter

from .views import RMAViewSet

router = DefaultRouter()
router.register("", RMAViewSet, basename="rma")

urlpatterns = router.urls
