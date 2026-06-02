import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../services/api';

export default function OrderConfirmation() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrder();
  }, [orderId]);

  const fetchOrder = async () => {
    try {
      const response = await api.get('/orders');
      const foundOrder = response.data.find(o => o.id === parseInt(orderId));
      setOrder(foundOrder);
    } catch (error) {
      console.error('Error fetching order:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 text-xl">Order not found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="text-center mb-8">
        <div className="inline-block p-4 bg-green-100 rounded-full mb-4">
          <svg className="h-16 w-16 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Order Confirmed!</h1>
        <p className="text-gray-600">Thank you for your purchase. Your order has been placed successfully.</p>
      </div>

      <div className="card p-6">
        <div className="border-b pb-4 mb-4">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Order Details</h2>
          <p className="text-gray-600">Order ID: #{order.id}</p>
          <p className="text-gray-600">Status: <span className="capitalize text-blue-600 font-semibold">{order.status}</span></p>
          <p className="text-gray-600">Date: {new Date(order.created_at).toLocaleDateString()}</p>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Items Ordered</h3>
          <div className="space-y-3">
            {order.items.map((item) => (
              <div key={item.id} className="flex justify-between items-center">
                <div className="flex items-center space-x-3">
                  {item.product?.image_url && (
                    <img src={item.product.image_url} alt={item.product.name} className="h-12 w-12 object-cover rounded" />
                  )}
                  <div>
                    <p className="font-medium">{item.product?.name}</p>
                    <p className="text-sm text-gray-600">Qty: {item.quantity} x ${item.price_at_time.toFixed(2)}</p>
                  </div>
                </div>
                <span className="font-semibold">${(item.price_at_time * item.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t pt-4 mb-6">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Delivery Address:</span>
              <span className="text-right">{order.address}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Phone:</span>
              <span>{order.phone}</span>
            </div>
          </div>
        </div>

        <div className="border-t pt-4">
          <div className="flex justify-between text-xl font-bold">
            <span>Total Amount</span>
            <span className="text-blue-600">${order.total_amount.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="text-center mt-8">
        <Link to="/" className="btn-primary">
          Continue Shopping
        </Link>
      </div>
    </div>
  );
}