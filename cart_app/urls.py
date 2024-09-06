from django.urls import path
from . import views
from django.urls import path



urlpatterns = [
    
    
    path("shop_cart/", views.shop_cart, name="shop_cart"),
    path("add_to_cart/<int:pro_id>/", views.add_to_cart, name="add_to_cart"),
    path("delete_cart_items/<int:pro_id>/",views.delete_cart_items,name="delete_cart_items",),
    
    
    path("check_stock/", views.check_stock, name="check_stock"),
    path("update_total_price/", views.update_total_price, name="update_total_price"),
    path("checkout/", views.checkout, name="checkout"),
    path("add_address_checkout/", views.add_address_checkout, name="add_address_"),
    
    path("place_order/", views.place_order, name="place_order"),
    
   
   
   
    path("order_detail/", views.order_detail, name="order_detail"),
    path("view_order/<int:ord_id>/", views.view_order, name="view_order"),
    path("view_status/<int:order_id>/", views.view_status, name="view_status"),
    path("view_all_order/", views.view_all_order, name="view_all_order"),
    
    path("wishlist_view/", views.wishlist_view, name="wishlist_view"),
    path("wishlist_add/<int:pro_id>/", views.wishlist_add, name="wishlist_add"),
    path("wishlist_del/<int:pro_id>/", views.wishlist_del, name="wishlist_del"),
    
    
    
    path("request_cancel_order/<int:order_id>/",views.request_cancel_order,name="request_cancel_order",),
    path("request_return_product/<int:orderItem_id>/",views.request_return_product,name="request_return_product",),
   
    path("payment_failure/", views.payment_failure, name="payment_failure"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("retry-payment/", views.retry_payment, name="retry_payment"),
   

    path('search/', views.search_products, name='search_products'),

   

    path('admin/refund_order/<int:order_item_id>/',views. refund_order, name='refund_order'),



    
    path('payment/status/<int:payment_id>/',views. payment_status, name='payment_status'),

]

