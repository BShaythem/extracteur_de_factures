import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Button,
  Box,
  Paper,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Divider,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Save as SaveIcon,
  Edit as EditIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import api from '../services/api';

const InvoiceDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [addItemDialog, setAddItemDialog] = useState(false);
  const [newItem, setNewItem] = useState({
    description: '',
    quantity: '',
    unit_price: '',
    total_price: '',
  });

  useEffect(() => {
    fetchInvoice();
  }, [id]);

  const fetchInvoice = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/invoice/${id}`);
      setInvoice(response.data);
    } catch (error) {
      setError('Failed to load invoice');
      console.error('Error fetching invoice:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setInvoice(prev => ({
      ...prev,
      extracted_fields: {
        ...prev.extracted_fields,
        [fieldName]: {
          ...prev.extracted_fields[fieldName],
          selected: value,
        },
      },
    }));
  };

  const handleItemAdd = () => {
    if (!newItem.description || !newItem.quantity || !newItem.unit_price) {
      setError('Please fill in all required fields');
      return;
    }

    const totalPrice = (parseFloat(newItem.quantity) * parseFloat(newItem.unit_price)).toFixed(2);
    const item = {
      description: newItem.description,
      quantity: newItem.quantity,
      unit_price: newItem.unit_price,
      total_price: totalPrice,
    };

    setInvoice(prev => ({
      ...prev,
      extracted_fields: {
        ...prev.extracted_fields,
        items: {
          ...prev.extracted_fields.items,
          selected: [...(prev.extracted_fields.items.selected || []), item],
        },
      },
    }));

    setNewItem({
      description: '',
      quantity: '',
      unit_price: '',
      total_price: '',
    });
    setAddItemDialog(false);
  };

  const handleItemDelete = (index) => {
    setInvoice(prev => ({
      ...prev,
      extracted_fields: {
        ...prev.extracted_fields,
        items: {
          ...prev.extracted_fields.items,
          selected: prev.extracted_fields.items.selected.filter((_, i) => i !== index),
        },
      },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');

    try {
              await api.put(`/invoice/${id}`, {
        extracted_fields: invoice.extracted_fields,
      });

      setSuccess('Invoice updated successfully!');
      setEditMode(false);
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to update invoice');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this invoice?')) {
      return;
    }

    try {
              await api.delete(`/invoice/${id}`);
      navigate('/');
    } catch (error) {
      setError('Failed to delete invoice');
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const renderField = (fieldName, field) => {
    const hasCandidates = field.candidates && field.candidates.length > 0;
    const confidence = hasCandidates ? field.candidates[0]?.confidence : null;

    return (
      <Grid item xs={12} sm={6} key={fieldName}>
        <Paper sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
              {fieldName.replace(/_/g, ' ')}
            </Typography>
            {confidence && (
              <Chip
                label={`${(confidence * 100).toFixed(1)}%`}
                color={getConfidenceColor(confidence)}
                size="small"
              />
            )}
          </Box>

          {hasCandidates && field.candidates.length > 1 ? (
            <FormControl fullWidth size="small">
              <Select
                value={field.selected || ''}
                onChange={(e) => handleFieldChange(fieldName, e.target.value)}
                disabled={!editMode}
              >
                {field.candidates.map((candidate, index) => (
                  <MenuItem key={index} value={candidate.value}>
                    <Box display="flex" justifyContent="space-between" width="100%">
                      <span>{candidate.value}</span>
                      <Chip
                        label={`${(candidate.confidence * 100).toFixed(1)}%`}
                        color={getConfidenceColor(candidate.confidence)}
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : (
            <TextField
              fullWidth
              size="small"
              value={field.selected || ''}
              onChange={(e) => handleFieldChange(fieldName, e.target.value)}
              disabled={!editMode}
            />
          )}
        </Paper>
      </Grid>
    );
  };

  const renderItems = () => {
    const items = invoice?.extracted_fields?.items?.selected || [];
    
    return (
      <Grid item xs={12}>
        <Paper sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Line Items</Typography>
            {editMode && (
              <Button
                startIcon={<AddIcon />}
                onClick={() => setAddItemDialog(true)}
                size="small"
              >
                Add Item
              </Button>
            )}
          </Box>

          {items.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No items found
            </Typography>
          ) : (
            <Grid container spacing={2}>
              {items.map((item, index) => (
                <Grid item xs={12} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Box flex={1}>
                          <Typography variant="body2" fontWeight="bold">
                            {item.description}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Qty: {item.quantity} × ${item.unit_price} = ${item.total_price}
                          </Typography>
                        </Box>
                        {editMode && (
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleItemDelete(index)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Paper>
      </Grid>
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!invoice) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Alert severity="error">Invoice not found</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box display="flex" alignItems="center">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/')}
            sx={{ mr: 2 }}
          >
            Back to Dashboard
          </Button>
          <Typography variant="h4" component="h1">
            Invoice Details
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<EditIcon />}
            onClick={() => setEditMode(!editMode)}
          >
            {editMode ? 'View Mode' : 'Edit Mode'}
          </Button>
          {editMode && (
            <Button
              variant="contained"
              startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          )}
          <Button
            variant="outlined"
            color="error"
            onClick={handleDelete}
          >
            Delete
          </Button>
        </Box>
      </Box>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Image Preview */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Invoice Image
            </Typography>
            <img
              src={`http://localhost:5000/invoices/${id}/image`}
              alt="Invoice"
              style={{
                width: '100%',
                height: 'auto',
                maxHeight: '500px',
                objectFit: 'contain',
              }}
            />
          </Paper>
        </Grid>

        {/* Invoice Details */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">Invoice Information</Typography>
              <Box display="flex" gap={1}>
                <Chip label={invoice.method || 'unknown'} color="primary" size="small" />
                <Chip label={invoice.status || 'unknown'} color="success" size="small" />
              </Box>
            </Box>
            
            <Grid container spacing={2}>
              {Object.entries(invoice.extracted_fields).map(([fieldName, field]) => {
                if (fieldName === 'items') return null;
                return renderField(fieldName, field);
              })}
            </Grid>
            
            <Divider sx={{ my: 3 }} />
            {renderItems()}
          </Paper>
        </Grid>
      </Grid>

      {/* Add Item Dialog */}
      <Dialog open={addItemDialog} onClose={() => setAddItemDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Line Item</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={newItem.description}
                onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Quantity"
                type="number"
                value={newItem.quantity}
                onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Unit Price"
                type="number"
                value={newItem.unit_price}
                onChange={(e) => setNewItem({ ...newItem, unit_price: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddItemDialog(false)}>Cancel</Button>
          <Button onClick={handleItemAdd} variant="contained">Add Item</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default InvoiceDetail; 