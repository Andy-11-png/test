import os
from flask import Blueprint, request, jsonify, current_app, render_template
from app.models.policy import Policy
from app.utils.pdf_processor import extract_text_from_pdf, save_pdf_file
from app import db
from flask_login import login_required, current_user

policy_bp = Blueprint('policy', __name__)

@policy_bp.route('/', methods=['GET'])
@login_required
def list():
    """Render the policy list page"""
    policies = Policy.query.filter_by(is_active=True).all()
    return render_template('policy/list.html', policies=policies)

@policy_bp.route('/create', methods=['GET'])
@login_required
def create():
    """Render the create policy page"""
    return render_template('policy/edit.html')

@policy_bp.route('/edit/<int:policy_id>', methods=['GET'])
@login_required
def edit(policy_id):
    """Render the edit policy page"""
    policy = Policy.query.get_or_404(policy_id)
    return render_template('policy/edit.html', policy=policy)

@policy_bp.route('/view/<int:policy_id>', methods=['GET'])
@login_required
def view_policy(policy_id):
    """Render the policy detail page"""
    policy = Policy.query.get_or_404(policy_id)
    return render_template('policy/detail.html', policy=policy)

@policy_bp.route('/api/policies', methods=['GET'])
def get_policies():
    """Get all active policies"""
    policies = Policy.query.filter_by(is_active=True).all()
    return jsonify([policy.to_dict() for policy in policies])

@policy_bp.route('/api/policies/<int:policy_id>', methods=['GET'])
def get_policy(policy_id):
    """Get a specific policy"""
    policy = Policy.query.get_or_404(policy_id)
    return jsonify(policy.to_dict())

@policy_bp.route('/api/policies', methods=['POST'])
@login_required
def create_policy():
    """Create a new policy"""
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400

    pdf_file = request.files['pdf_file']
    title = request.form.get('title')
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    try:
        # Extract text from PDF
        content = extract_text_from_pdf(pdf_file)
        if not content:
            return jsonify({'error': 'Could not extract text from PDF'}), 400
            
        # Save PDF file
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'policies')
        pdf_path = save_pdf_file(pdf_file, upload_folder)
        
        # Create policy
        policy = Policy(
            title=title,
            content=content,
            pdf_path=pdf_path,
            created_by=current_user.id
        )
        
        db.session.add(policy)
        db.session.commit()
        
        return jsonify(policy.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@policy_bp.route('/api/policies/<int:policy_id>', methods=['PUT'])
@login_required
def update_policy(policy_id):
    """Update an existing policy"""
    policy = Policy.query.get_or_404(policy_id)
    
    title = request.form.get('title')
    content = request.form.get('content')
    
    if title:
        policy.title = title
    if content:
        policy.content = content
    
    if 'pdf_file' in request.files and request.files['pdf_file'].filename:
        # Update with new PDF
        pdf_file = request.files['pdf_file']
        try:
            content = extract_text_from_pdf(pdf_file)
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'policies')
            pdf_path = save_pdf_file(pdf_file, upload_folder)
            
            # Delete old PDF if exists
            if policy.pdf_path and os.path.exists(policy.pdf_path):
                os.remove(policy.pdf_path)
                
            policy.content = content
            policy.pdf_path = pdf_path
            
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    db.session.commit()
    return jsonify(policy.to_dict())

@policy_bp.route('/api/policies/<int:policy_id>', methods=['DELETE'])
@login_required
def delete_policy(policy_id):
    """Delete a policy (soft delete)"""
    policy = Policy.query.get_or_404(policy_id)
    policy.is_active = False
    db.session.commit()
    return jsonify({'message': 'Policy deleted successfully'}) 