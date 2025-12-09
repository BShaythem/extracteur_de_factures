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
import Autocomplete from '@mui/material/Autocomplete';
import {
  ArrowBack as ArrowBackIcon,
  Save as SaveIcon,
  Edit as EditIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const InvoiceDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
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
  const [zoom, setZoom] = useState(1);

  const orderedGroups = [
    { title: 'Supplier', fields: ['supplier_name', 'supplier_address'] },
    { title: 'Customer', fields: ['customer_name', 'customer_address'] },
    { title: 'Dates & Number', fields: ['invoice_date', 'due_date', 'invoice_number'] },
    { title: 'Tax & Totals', fields: ['tax_rate', 'tax_amount', 'invoice_subtotal', 'invoice_total'] },
  ];

  useEffect(() => {
    if (user) {
      fetchInvoice();
    }
  }, [id, user]);

  const fetchInvoice = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/invoice/invoices/${id}`);
      setInvoice(response.data);
    } catch (error) {
      if (error.response?.status === 401) {
        // User is not authenticated, redirect to login
        navigate('/login');
        return;
      }
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
              await api.put(`/invoice/invoices/${id}`, {
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
              await api.delete(`/invoice/invoices/${id}`);
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
    const candidates = field?.candidates || [];
    const selectedValue = field?.selected || '';

    return (
      <Grid xs={12} md={6} key={fieldName}>
        <Paper sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
              {fieldName.replace(/_/g, ' ')}
            </Typography>
            {candidates[0]?.confidence != null && (
              <Chip label={`${(candidates[0].confidence * 100).toFixed(1)}%`} color={getConfidenceColor(candidates[0].confidence)} size="small" />
            )}
          </Box>

          <Autocomplete
            freeSolo
            disableClearable
            options={candidates.map(c => c.value)}
            value={selectedValue}
            onChange={(_, val) => editMode && handleFieldChange(fieldName, val || '')}
            onInputChange={(_, val, reason) => {
              if (!editMode) return;
              if (reason === 'input') handleFieldChange(fieldName, val);
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                size="small"
                disabled={!editMode}
                placeholder={candidates.length > 0 ? 'Choose or type a custom value' : 'Type value'}
              />
            )}
          />
        </Paper>
      </Grid>
    );
  };

  const renderItems = () => {
    const items = invoice?.extracted_fields?.items?.selected || [];

    return (
      <Grid xs={12}>
        <Paper sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Line Items</Typography>
            {editMode && (
              <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={() => setAddItemDialog(true)}>
                Add Item
              </Button>
            )}
          </Box>

          {items.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No items found</Typography>
          ) : (
            <Grid container spacing={2}>
              {items.map((item, idx) => (
                <Grid xs={12} key={idx}>
                  <Card variant="outlined">
                    <CardContent>
                      <Grid container spacing={2} alignItems="center">
                        <Grid xs={6}>
                          <TextField
                            fullWidth
                            label="Description"
                            size="small"
                            value={item.description}
                            onChange={(e) => {
                              if (!editMode) return;
                              const v = e.target.value;
                              setInvoice(prev => {
                                const itemsUpd = [...(prev.extracted_fields.items.selected || [])];
                                itemsUpd[idx] = { ...itemsUpd[idx], description: v };
                                return { ...prev, extracted_fields: { ...prev.extracted_fields, items: { ...prev.extracted_fields.items, selected: itemsUpd } } };
                              });
                            }}
                            disabled={!editMode}
                          />
                        </Grid>
                        <Grid xs={2}>
                          <TextField
                            fullWidth
                            label="Qty"
                            size="small"
                            type="number"
                            value={item.quantity}
                            onChange={(e) => {
                              if (!editMode) return;
                              const v = e.target.value;
                              setInvoice(prev => {
                                const itemsUpd = [...(prev.extracted_fields.items.selected || [])];
                                itemsUpd[idx] = { ...itemsUpd[idx], quantity: v };
                                return { ...prev, extracted_fields: { ...prev.extracted_fields, items: { ...prev.extracted_fields.items, selected: itemsUpd } } };
                              });
                            }}
                            disabled={!editMode}
                          />
                        </Grid>
                        <Grid xs={2}>
                          <TextField
                            fullWidth
                            label="Unit"
                            size="small"
                            type="number"
                            value={item.unit_price}
                            onChange={(e) => {
                              if (!editMode) return;
                              const v = e.target.value;
                              setInvoice(prev => {
                                const itemsUpd = [...(prev.extracted_fields.items.selected || [])];
                                itemsUpd[idx] = { ...itemsUpd[idx], unit_price: v };
                                return { ...prev, extracted_fields: { ...prev.extracted_fields, items: { ...prev.extracted_fields.items, selected: itemsUpd } } };
                              });
                            }}
                            disabled={!editMode}
                          />
                        </Grid>
                        <Grid xs={2}>
                          <TextField
                            fullWidth
                            label="Total"
                            size="small"
                            type="number"
                            value={item.total_price}
                            onChange={(e) => {
                              if (!editMode) return;
                              const v = e.target.value;
                              setInvoice(prev => {
                                const itemsUpd = [...(prev.extracted_fields.items.selected || [])];
                                itemsUpd[idx] = { ...itemsUpd[idx], total_price: v };
                                return { ...prev, extracted_fields: { ...prev.extracted_fields, items: { ...prev.extracted_fields.items, selected: itemsUpd } } };
                              });
                            }}
                            disabled={!editMode}
                          />
                        </Grid>
                      </Grid>
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

  if (loading || authLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    // User is not authenticated, redirect to login
    navigate('/login');
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

      {/* Side-by-side layout like Results */}
      <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start' }}>
        {/* Left: Image with zoom */}
        <Box sx={{ flex: '0 0 55%', minWidth: 0 }}>
          <Paper sx={{ p: 2, height: '85vh', display: 'flex', flexDirection: 'column' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">Invoice Image</Typography>
              {invoice?.image_exists && (
                <Box display="flex" gap={1}>
                  <Button size="small" variant="outlined" onClick={() => setZoom(z => Math.max(0.5, +(z - 0.1).toFixed(2)))}>-</Button>
                  <Typography variant="body2" sx={{ mx: 1 }}>{Math.round(zoom * 100)}%</Typography>
                  <Button size="small" variant="outlined" onClick={() => setZoom(z => Math.min(3, +(z + 0.1).toFixed(2)))}>+</Button>
                  <Button size="small" onClick={() => setZoom(1)}>Reset</Button>
                </Box>
              )}
            </Box>
            <Box sx={{ overflow: 'auto', flex: 1, minHeight: 0, borderRadius: 1 }}>
              {invoice?.image_exists ? (
                <Box>
                  <img
                    src={`http://localhost:5000/api/invoice/invoices/${id}/image`}
                    alt="Invoice"
                    style={{ width: '100%', height: 'auto', transform: `scale(${zoom})`, transformOrigin: 'top left' }}
                    onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.style.display = 'none'; }}
                  />
                </Box>
              ) : (
                <Box
                  sx={{
                    height: 300,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: 'action.hover',
                    color: 'text.secondary',
                  }}
                >
                  No image available
                </Box>
              )}
            </Box>
          </Paper>
        </Box>

        {/* Right: Fields like Results */}
        <Box sx={{ flex: '1 0 45%', minWidth: 0 }}>
          <Paper sx={{ p: 2, height: '85vh', display: 'flex', flexDirection: 'column' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="h6">Extracted Fields</Typography>
              <Box display="flex" gap={1}>
                <Chip label={invoice.method || 'unknown'} color="primary" size="small" />
                <Chip label={invoice.status || 'unknown'} color="success" size="small" />
              </Box>
            </Box>

            <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
              <Grid container spacing={2}>
                {(() => {
                  const used = new Set();
                  const sections = [];

                  for (const group of orderedGroups) {
                    const present = group.fields.filter((name) => invoice?.extracted_fields?.[name]);
                    if (present.length === 0) continue;

                    sections.push(
                      <Grid xs={12} key={`group-${group.title}`}>
                        <Typography variant="subtitle2" sx={{ textTransform: 'uppercase', fontWeight: 700, color: 'text.secondary', mb: 1 }}>
                          {group.title}
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Grid container spacing={2}>
                          {present.map((fieldName) => {
                            used.add(fieldName);
                            const field = invoice.extracted_fields[fieldName];
                            return renderField(fieldName, field);
                          })}
                        </Grid>
                      </Grid>
                    );
                  }

                  const remaining = Object.entries(invoice?.extracted_fields || {})
                    .filter(([name]) => name !== 'items' && !used.has(name));
                  if (remaining.length) {
                    sections.push(
                      <Grid xs={12} key="group-other">
                        <Typography variant="subtitle2" sx={{ textTransform: 'uppercase', fontWeight: 700, color: 'text.secondary', mb: 1 }}>
                          Other
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Grid container spacing={2}>
                          {remaining.map(([name, field]) => renderField(name, field))}
                        </Grid>
                      </Grid>
                    );
                  }

                  return sections;
                })()}
              </Grid>

              <Divider sx={{ my: 3 }} />
              {renderItems()}
            </Box>
          </Paper>
        </Box>
      </Box>

      {/* Add Item Dialog */}
      <Dialog open={addItemDialog} onClose={() => setAddItemDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Line Item</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
                         <Grid xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={newItem.description}
                onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
              />
            </Grid>
            <Grid xs={6}>
              <TextField
                fullWidth
                label="Quantity"
                type="number"
                value={newItem.quantity}
                onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
              />
            </Grid>
            <Grid xs={6}>
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