import streamlit as st
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.utils.utils import run_paddle_ocr

class JSONLabelingTool:
    def __init__(self):
        self.setup_config()
        self.setup_session_state()
    
    def setup_config(self):
        """Setup configuration paths"""
        self.IMAGE_DIR = "data/invoices-donut/valid"
        self.JSON_DIR = "data/invoices-donut/donut_json"
        self.OUTPUT_DIR = "data/invoices-donut/corrected_json"
        
        # Create output directory if it doesn't exist
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        
        # Define expected fields
        self.FIELDS = [
            "supplier_name", "supplier_address", "customer_name", "customer_address",
            "invoice_number", "invoice_date", "due_date", "tax_amount", "tax_rate",
            "invoice_subtotal", "invoice_total"
        ]
        
        self.ITEM_FIELDS = [
            "item_description", "item_quantity", "item_unit_price", "item_total_price"
        ]
    
    def setup_session_state(self):
        """Initialize session state variables"""
        if 'current_file_idx' not in st.session_state:
            st.session_state.current_file_idx = 0
        if 'json_data' not in st.session_state:
            st.session_state.json_data = {}
        if 'ocr_tokens' not in st.session_state:
            st.session_state.ocr_tokens = []
        if 'selected_tokens' not in st.session_state:
            st.session_state.selected_tokens = []
        if 'current_field' not in st.session_state:
            st.session_state.current_field = None
    
    def load_image_files(self):
        """Load all image files from the directory"""
        if not os.path.exists(self.IMAGE_DIR):
            return []
        return sorted([f for f in os.listdir(self.IMAGE_DIR) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    def load_json_data(self, image_filename):
        """Load JSON data for the given image"""
        json_filename = os.path.splitext(image_filename)[0] + '.json'
        json_path = os.path.join(self.JSON_DIR, json_filename)
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_json_data(self, image_filename, data):
        """Save corrected JSON data"""
        json_filename = os.path.splitext(image_filename)[0] + '.json'
        json_path = os.path.join(self.OUTPUT_DIR, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        st.success(f"✅ Saved corrections to {json_filename}")
    
    def get_ocr_tokens(self, image_path):
        """Get OCR tokens with bounding boxes"""
        try:
            tokens = run_paddle_ocr(image_path)
            return tokens
        except Exception as e:
            st.error(f"Error running OCR: {str(e)}")
            return []
    
    def create_annotated_image(self, image_path, tokens, selected_tokens=None):
        """Create an annotated image with bounding boxes"""
        img = Image.open(image_path).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        for i, token in enumerate(tokens):
            bbox = token.get('orig_bbox', [0, 0, 0, 0])
            x0, y0, x1, y1 = bbox
            
            # Color coding
            if selected_tokens and i in selected_tokens:
                color = 'red'
                width = 3
            else:
                color = 'blue'
                width = 1
            
            # Draw bounding box
            draw.rectangle([x0, y0, x1, y1], outline=color, width=width)
            
            # Draw token index
            draw.text((x0, y0-15), str(i), fill=color, font=font)
        
        return img
    
    def create_interactive_plot(self, image_path, tokens):
        """Create an interactive Plotly plot for token selection"""
        img = Image.open(image_path).convert('RGB')
        img_array = np.array(img)
        
        fig = go.Figure()
        
        # Add image
        fig.add_layout_image(
            dict(
                source=img,
                xref="x",
                yref="y",
                x=0,
                y=0,
                sizex=img.width,
                sizey=img.height,
                sizing="stretch",
                opacity=0.8,
                layer="below"
            )
        )
        
        # Add bounding boxes as scatter points
        x_coords = []
        y_coords = []
        texts = []
        hover_texts = []
        
        for i, token in enumerate(tokens):
            bbox = token.get('orig_bbox', [0, 0, 0, 0])
            x0, y0, x1, y1 = bbox
            center_x = (x0 + x1) / 2
            center_y = (y0 + y1) / 2
            
            x_coords.append(center_x)
            y_coords.append(center_y)
            texts.append(str(i))
            hover_texts.append(f"Token {i}: {token.get('text', '')}")
        
        fig.add_trace(go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='markers+text',
            text=texts,
            textposition="middle center",
            hovertext=hover_texts,
            hoverinfo='text',
            marker=dict(
                size=20,
                color='rgba(255, 0, 0, 0.6)',
                line=dict(width=2, color='red')
            ),
            name='Tokens'
        ))
        
        fig.update_layout(
            width=800,
            height=600,
            xaxis=dict(range=[0, img.width], showgrid=False, zeroline=False),
            yaxis=dict(range=[img.height, 0], showgrid=False, zeroline=False),
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        return fig
    
    def render_json_editor(self, data):
        """Render JSON editor with field-specific inputs"""
        st.subheader("📝 JSON Editor")
        
        # Main fields
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Supplier Information**")
            data['supplier_name'] = st.text_input("Supplier Name", 
                                                 value=data.get('supplier_name', ''))
            data['supplier_address'] = st.text_area("Supplier Address", 
                                                   value=data.get('supplier_address', ''))
        
        with col2:
            st.write("**Customer Information**")
            data['customer_name'] = st.text_input("Customer Name", 
                                                 value=data.get('customer_name', ''))
            data['customer_address'] = st.text_area("Customer Address", 
                                                   value=data.get('customer_address', ''))
        
        # Invoice details
        col3, col4, col5 = st.columns(3)
        
        with col3:
            data['invoice_number'] = st.text_input("Invoice Number", 
                                                  value=data.get('invoice_number', ''))
            data['invoice_date'] = st.text_input("Invoice Date", 
                                                value=data.get('invoice_date', ''))
        
        with col4:
            data['due_date'] = st.text_input("Due Date", 
                                            value=data.get('due_date', ''))
            data['tax_rate'] = st.text_input("Tax Rate", 
                                           value=data.get('tax_rate', ''))
        
        with col5:
            data['invoice_subtotal'] = st.text_input("Subtotal", 
                                                    value=data.get('invoice_subtotal', ''))
            data['tax_amount'] = st.text_input("Tax Amount", 
                                              value=data.get('tax_amount', ''))
            data['invoice_total'] = st.text_input("Total", 
                                                 value=data.get('invoice_total', ''))
        
        # Items section
        st.write("**Items**")
        items = data.get('items', [])
        
        # Add new item button
        if st.button("➕ Add Item"):
            items.append({
                'item_description': '',
                'item_quantity': '',
                'item_unit_price': '',
                'item_total_price': ''
            })
        
        # Edit existing items
        for i, item in enumerate(items):
            with st.expander(f"Item {i+1}: {item.get('item_description', 'New Item')}"):
                col_desc, col_qty, col_price, col_total = st.columns(4)
                
                with col_desc:
                    item['item_description'] = st.text_input(
                        "Description", value=item.get('item_description', ''), 
                        key=f"desc_{i}")
                
                with col_qty:
                    item['item_quantity'] = st.text_input(
                        "Quantity", value=item.get('item_quantity', ''), 
                        key=f"qty_{i}")
                
                with col_price:
                    item['item_unit_price'] = st.text_input(
                        "Unit Price", value=item.get('item_unit_price', ''), 
                        key=f"price_{i}")
                
                with col_total:
                    item['item_total_price'] = st.text_input(
                        "Total Price", value=item.get('item_total_price', ''), 
                        key=f"total_{i}")
                
                if st.button(f"🗑️ Remove Item {i+1}", key=f"remove_{i}"):
                    items.pop(i)
                    st.experimental_rerun()
        
        data['items'] = items
        return data
    
    def render_token_selector(self, tokens):
        """Render token selection interface"""
        st.subheader("🎯 Token Selector")
        
        # Field selection
        all_fields = self.FIELDS + ['items'] + [f'item_{field}' for field in self.ITEM_FIELDS]
        selected_field = st.selectbox("Select field to assign tokens:", 
                                     [''] + all_fields)
        
        if selected_field:
            st.session_state.current_field = selected_field
            
            # Token selection
            st.write(f"**Select tokens for: {selected_field}**")
            
            # Display tokens in a table
            token_data = []
            for i, token in enumerate(tokens):
                token_data.append({
                    'Index': i,
                    'Text': token.get('text', ''),
                    'Select': False
                })
            
            df = pd.DataFrame(token_data)
            
            # Multi-select for tokens
            selected_indices = st.multiselect(
                "Choose tokens:",
                options=df['Index'].tolist(),
                format_func=lambda x: f"{x}: {df.iloc[x]['Text']}"
            )
            
            if selected_indices and st.button("✅ Assign Selected Tokens"):
                selected_text = ' '.join([tokens[i]['text'] for i in selected_indices])
                
                # Update JSON data based on field
                if selected_field in st.session_state.json_data:
                    st.session_state.json_data[selected_field] = selected_text
                elif selected_field.startswith('item_'):
                    # Handle item fields
                    st.info("Item field assignment - implement item-specific logic here")
                
                st.success(f"Assigned tokens to {selected_field}: {selected_text}")
                st.experimental_rerun()
    
    def run(self):
        """Main application runner"""
        st.set_page_config(
            page_title="Invoice JSON Labeling Tool",
            page_icon="📄",
            layout="wide"
        )
        
        st.title("📄 Invoice JSON Labeling Tool")
        st.markdown("---")
        
        # Load image files
        image_files = self.load_image_files()
        
        if not image_files:
            st.error(f"No image files found in {self.IMAGE_DIR}")
            return
        
        # File navigation
        col1, col2, col3, col4 = st.columns([1, 3, 1, 1])
        
        with col1:
            if st.button("⬅️ Previous") and st.session_state.current_file_idx > 0:
                st.session_state.current_file_idx -= 1
                st.experimental_rerun()
        
        with col2:
            current_file = st.selectbox(
                "Select Invoice:",
                options=range(len(image_files)),
                index=st.session_state.current_file_idx,
                format_func=lambda x: f"{x+1}/{len(image_files)}: {image_files[x]}"
            )
            st.session_state.current_file_idx = current_file
        
        with col3:
            if st.button("➡️ Next") and st.session_state.current_file_idx < len(image_files) - 1:
                st.session_state.current_file_idx += 1
                st.experimental_rerun()
        
        with col4:
            progress = (st.session_state.current_file_idx + 1) / len(image_files)
            st.metric("Progress", f"{st.session_state.current_file_idx + 1}/{len(image_files)}")
        
        # Current file
        current_filename = image_files[st.session_state.current_file_idx]
        current_image_path = os.path.join(self.IMAGE_DIR, current_filename)
        
        # Load data
        st.session_state.json_data = self.load_json_data(current_filename)
        st.session_state.ocr_tokens = self.get_ocr_tokens(current_image_path)
        
        # Main interface
        col_image, col_json = st.columns([1, 1])
        
        with col_image:
            st.subheader("🖼️ Invoice Image")
            
            # Display image
            if os.path.exists(current_image_path):
                # Create interactive plot
                fig = self.create_interactive_plot(current_image_path, st.session_state.ocr_tokens)
                st.plotly_chart(fig, use_container_width=True)
                
                # Token selector
                self.render_token_selector(st.session_state.ocr_tokens)
            else:
                st.error(f"Image not found: {current_image_path}")
        
        with col_json:
            # JSON editor
            st.session_state.json_data = self.render_json_editor(st.session_state.json_data)
            
            # Save button
            if st.button("💾 Save Corrections", type="primary"):
                self.save_json_data(current_filename, st.session_state.json_data)
            
            # Raw JSON view
            with st.expander("🔍 Raw JSON View"):
                st.json(st.session_state.json_data)
        
        # Statistics
        st.markdown("---")
        st.subheader("📊 Dataset Statistics")
        
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        
        with col_stats1:
            st.metric("Total Images", len(image_files))
        
        with col_stats2:
            corrected_files = len([f for f in os.listdir(self.OUTPUT_DIR) 
                                 if f.endswith('.json')]) if os.path.exists(self.OUTPUT_DIR) else 0
            st.metric("Corrected Files", corrected_files)
        
        with col_stats3:
            completion_rate = (corrected_files / len(image_files)) * 100 if image_files else 0
            st.metric("Completion Rate", f"{completion_rate:.1f}%")

if __name__ == "__main__":
    app = JSONLabelingTool()
    app.run()