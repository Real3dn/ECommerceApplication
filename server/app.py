import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, Product, CartItem, Order, OrderItem
from auth import admin_required, user_required
from datetime import timedelta

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Configure JWT
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'
jwt = JWTManager(app)

db.init_app(app)

# JWT error handlers
@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'error': 'Invalid token',
        'msg': str(error)
    }), 422

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'error': 'Authorization required',
        'msg': str(error)
    }), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'error': 'Token has expired',
        'msg': 'The token has expired'
    }), 401

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Create database tables
with app.app_context():
    db.create_all()
    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin/admin123")

# Auth Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Use string identity
    access_token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=7))
    
    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict(),
        'access_token': access_token
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Use string identity
    access_token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=7))
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token
    }), 200

@app.route('/api/auth/me', methods=['GET'])
@user_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200

# ... rest of the routes remain the same, but update all get_jwt_identity() calls ...

# Product Routes
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([product.to_dict() for product in products]), 200

@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    product = Product.query.get_or_404(id)
    return jsonify(product.to_dict()), 200

@app.route('/api/products', methods=['POST'])
@admin_required()
def create_product():
    # Check if the request has files or is JSON
    if request.files:
        # Handle multipart form data
        data = request.form
        image_file = request.files.get('image')
    else:
        # Handle JSON data
        data = request.get_json()
        image_file = None
    
    if not data or not data.get('name') or not data.get('price'):
        return jsonify({'error': 'Name and price are required'}), 400
    
    image_url = None
    if image_file and allowed_file(image_file.filename):
        filename = str(uuid.uuid4()) + '_' + secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        image_url = f'/api/uploads/{filename}'
    
    product = Product(
        name=data['name'],
        description=data.get('description', ''),
        price=float(data['price']),
        image_url=image_url
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify(product.to_dict()), 201

@app.route('/api/products/<int:id>', methods=['PUT'])
@admin_required()
def update_product(id):
    product = Product.query.get_or_404(id)
    
    # Check if the request has files or is JSON
    if request.files:
        data = request.form
        image_file = request.files.get('image')
    else:
        data = request.get_json()
        image_file = None
    
    if data:
        product.name = data.get('name', product.name)
        product.description = data.get('description', product.description)
        if 'price' in data:
            product.price = float(data['price'])
    
    if image_file and allowed_file(image_file.filename):
        # Delete old image if exists
        if product.image_url:
            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_url.split('/')[-1])
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        
        filename = str(uuid.uuid4()) + '_' + secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        product.image_url = f'/api/uploads/{filename}'
    
    db.session.commit()
    
    return jsonify(product.to_dict()), 200

@app.route('/api/products/<int:id>', methods=['DELETE'])
@admin_required()
def delete_product(id):
    product = Product.query.get_or_404(id)
    
    # Delete image file if exists
    if product.image_url:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_url.split('/')[-1])
        if os.path.exists(image_path):
            os.remove(image_path)
    
    # First, delete all cart items referencing this product across ALL users
    CartItem.query.filter_by(product_id=id).delete()
    
    # For order items, we keep them but they'll show as "Product Unavailable"
    # No need to modify order_items as they keep price_at_time for historical records
    
    # Now delete the product
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'message': 'Product deleted successfully'}), 200

# Upload Routes
@app.route('/api/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Cart Routes
@app.route('/api/cart', methods=['GET'])
@user_required()
def get_cart():
    user_id = int(get_jwt_identity())
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    return jsonify([item.to_dict() for item in cart_items]), 200

@app.route('/api/cart', methods=['POST'])
@user_required()
def add_to_cart():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('product_id'):
        return jsonify({'error': 'Product ID is required'}), 400
    
    product = Product.query.get_or_404(data['product_id'])
    quantity = data.get('quantity', 1)
    
    # Check if product already in cart
    cart_item = CartItem.query.filter_by(user_id=user_id, product_id=data['product_id']).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=user_id, product_id=data['product_id'], quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    
    return jsonify(cart_item.to_dict()), 200

@app.route('/api/cart/<int:id>', methods=['PUT'])
@user_required()
def update_cart_item(id):
    user_id = int(get_jwt_identity())
    cart_item = CartItem.query.filter_by(id=id, user_id=user_id).first_or_404()
    data = request.get_json()
    
    if 'quantity' in data:
        if data['quantity'] <= 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = data['quantity']
        db.session.commit()
    
    return jsonify(cart_item.to_dict() if data.get('quantity', 0) > 0 else {'message': 'Item removed'}), 200

@app.route('/api/cart/<int:id>', methods=['DELETE'])
@user_required()
def remove_from_cart(id):
    user_id = int(get_jwt_identity())
    cart_item = CartItem.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    db.session.delete(cart_item)
    db.session.commit()
    
    return jsonify({'message': 'Item removed from cart'}), 200

# Order Routes
@app.route('/api/orders', methods=['POST'])
@user_required()
def create_order():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('address') or not data.get('phone'):
        return jsonify({'error': 'Address and phone are required'}), 400
    
    # Get cart items
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    
    order = Order(
        user_id=user_id,
        address=data['address'],
        phone=data['phone'],
        total_amount=total_amount,
        status='pending'
    )
    
    db.session.add(order)
    
    # Create order items and clear cart
    for cart_item in cart_items:
        order_item = OrderItem(
            order=order,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price_at_time=cart_item.product.price
        )
        db.session.add(order_item)
        db.session.delete(cart_item)
    
    db.session.commit()
    
    return jsonify(order.to_dict()), 201

@app.route('/api/orders', methods=['GET'])
@user_required()
def get_user_orders():
    user_id = int(get_jwt_identity())
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return jsonify([order.to_dict() for order in orders]), 200

@app.route('/api/orders/admin', methods=['GET'])
@admin_required()
def get_all_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify([order.to_dict() for order in orders]), 200

@app.route('/api/orders/<int:id>/status', methods=['PUT'])
@admin_required()
def update_order_status(id):
    order = Order.query.get_or_404(id)
    data = request.get_json()
    
    valid_statuses = ['pending', 'processing', 'shipped', 'delivered']
    if data.get('status') not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
    
    order.status = data['status']
    db.session.commit()
    
    return jsonify(order.to_dict()), 200

# Stats endpoint for admin dashboard
@app.route('/api/admin/stats', methods=['GET'])
@admin_required()
def get_admin_stats():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return jsonify({
        'total_products': total_products,
        'total_orders': total_orders,
        'recent_orders': [order.to_dict() for order in recent_orders]
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)