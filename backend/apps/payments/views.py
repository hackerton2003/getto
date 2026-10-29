from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.v1.permissions import IsCustomer
from api.v1.serializers.payments import PaymentCreateSerializer, PaymentSerializer, ReceiptSerializer
from api.v1.utils import raise_api_validation
from apps.bookings.models import Booking
from apps.payments.models import Payment, Receipt
from services.payments import PaymentService


class PaymentListCreateView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={200: PaymentSerializer(many=True)}, operation_id="payments_list")
    def get(self, request):
        payments = Payment.objects.filter(customer_id=request.user.pk).select_related("booking")
        return Response(PaymentSerializer(payments, many=True).data)

    @extend_schema(request=PaymentCreateSerializer, responses={201: PaymentSerializer}, operation_id="payments_create")
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = get_object_or_404(
            Booking,
            pk=serializer.validated_data["booking_id"].pk,
            customer_id=request.user.pk,
        )
        try:
            payment = PaymentService.create_payment(
                booking_id=booking.pk,
                payment_method=serializer.validated_data["payment_method"],
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentDetailView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={200: PaymentSerializer}, operation_id="payments_retrieve")
    def get(self, request, payment_id):
        payment = get_object_or_404(
            Payment.objects.select_related("booking"),
            pk=payment_id,
            customer_id=request.user.pk,
        )
        return Response(PaymentSerializer(payment).data)


class ReceiptListView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={200: ReceiptSerializer(many=True)}, operation_id="receipts_list")
    def get(self, request):
        receipts = Receipt.objects.filter(payment__customer_id=request.user.pk).select_related("payment")
        return Response(ReceiptSerializer(receipts, many=True).data)
