# Invoice Extraction Frontend

A modern React application for extracting and managing invoice data using AI models.

## Features

- 🔐 **User Authentication** - Secure login and registration
- 📁 **Drag & Drop Upload** - Easy file upload with support for images and PDFs
- 🤖 **Multiple AI Models** - LayoutLMv3, LLM (Groq/Ollama), and Donut
- 📊 **Confidence Scores** - Visual confidence indicators for extracted fields
- ✏️ **Inline Editing** - Edit extracted fields with multiple candidate options
- 💾 **Save & Manage** - Save invoices to your account and manage them
- 📱 **Responsive Design** - Works on desktop and mobile devices

## Pages

- **Login/Register** - User authentication
- **Dashboard** - View all saved invoices with search and filtering
- **Extraction** - Upload files and choose extraction method
- **Results** - View and edit extracted data before saving
- **Invoice Detail** - View and edit saved invoices

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Make sure the backend API is running on `http://localhost:5000`

## Technologies Used

- **React 18** - Frontend framework
- **Vite** - Build tool and dev server
- **Material-UI (MUI)** - UI component library
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls
- **React Dropzone** - File upload component

## Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
