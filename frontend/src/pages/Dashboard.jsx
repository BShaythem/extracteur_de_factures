import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Button,
  Box,
  Card,
  CardContent,
  CardMedia,
  CardActionArea,
  Grid,
  TextField,
  IconButton,
  Chip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  MoreVert as MoreVertIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

const Dashboard = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [error, setError] = useState('');
  
  const { user, loading: authLoading, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      fetchInvoices();
    }
  }, [user]);

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const response = await api.get('/invoice/invoices');
      setInvoices(response.data.invoices || []); // Handle the nested structure
      setError(''); // Clear any previous errors
    } catch (error) {
      console.error('Error fetching invoices:', error);
      if (error.response?.status === 401) {
        // User is not authenticated, redirect to login
        navigate('/login');
        return;
      }
      setInvoices([]); // Set empty array on error
      setError(''); // Clear error - no invoices is normal
    } finally {
      setLoading(false);
    }
  };

  const handleMenuClick = (event, invoice) => {
    setAnchorEl(event.currentTarget);
    setSelectedInvoice(invoice);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    // setSelectedInvoice(null); // Remove this line
  };

  const handleViewInvoice = () => {
    if (selectedInvoice) {
      navigate(`/invoice/${selectedInvoice.id}`);
    }
    handleMenuClose();
  };

  const handleEditInvoice = () => {
    if (selectedInvoice) {
      navigate(`/invoice/${selectedInvoice.id}`);
    }
    handleMenuClose();
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
    handleMenuClose();
  };

  const handleDeleteConfirm = async () => {
    if (!selectedInvoice) return;

    try {
              await api.delete(`/invoice/invoices/${selectedInvoice.id}`);
      setInvoices(invoices.filter(inv => inv.id !== selectedInvoice.id));
      setDeleteDialogOpen(false);
    } catch (error) {
      setError('Failed to delete invoice');
      console.error('Error deleting invoice:', error);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const filteredInvoices = invoices.filter(invoice =>
    invoice.invoice_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    invoice.supplier_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    invoice.customer_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const getMethodColor = (method) => {
    switch (method) {
      case 'layoutlmv3': return 'primary';
      case 'llm': return 'secondary';
      case 'donut': return 'info';
      default: return 'default';
    }
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

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Invoice Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Welcome back, {user?.username}
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/extract')}
          >
            Extract New Invoice
          </Button>
          <IconButton onClick={handleLogout} color="inherit">
            <LogoutIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Search */}
      <Box mb={3}>
        <TextField
          fullWidth
          placeholder="Search invoices by number, supplier, or customer..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
          }}
        />
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Invoices Grid */}
      {filteredInvoices.length === 0 ? (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No invoices found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {searchTerm ? 'Try adjusting your search terms' : 'Start by extracting your first invoice'}
          </Typography>
          {!searchTerm && (
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/extract')}
              sx={{ mt: 2 }}
            >
              Extract Invoice
            </Button>
          )}
        </Box>
      ) : (
        <Grid container spacing={3} alignItems="stretch">
          {filteredInvoices.map((invoice) => (
            <Grid key={invoice.id} sx={{ width: { xs: '100%', sm: '50%', md: '33.33%', lg: '20%' }, display: 'flex', flexDirection: 'column', height: 360 }}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative', width: '100%' }}>
                {/* Three dots menu absolutely at top right, outside CardActionArea */}
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); handleMenuClick(e, invoice); }}
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    bgcolor: 'rgba(255,255,255,0.85)',
                    boxShadow: 1,
                    '&:hover': { bgcolor: 'rgba(240,240,240,1)' },
                    zIndex: 2,
                  }}
                >
                  <MoreVertIcon />
                </IconButton>
                <CardActionArea onClick={() => navigate(`/invoice/${invoice.id}`)} sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'stretch', minHeight: 0 }}>
                  {invoice.image_exists ? (
                    <CardMedia
                      component="img"
                      height="140"
                      image={`http://localhost:5000/api/invoice/invoices/${invoice.id}/image`}
                      alt="Invoice"
                      sx={{ objectFit: 'cover', flexShrink: 0 }}
                      onError={(e) => {
                        e.currentTarget.onerror = null;
                        e.currentTarget.src = '/vite.svg';
                      }}
                    />
                  ) : (
                    <Box
                      sx={{
                        height: 140,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: 'action.hover',
                        color: 'text.secondary',
                        width: '100%',
                        flexShrink: 0
                      }}
                    >
                      No image available
                    </Box>
                  )}
                  <CardContent sx={{ flex: '1 1 0', display: 'flex', flexDirection: 'column', overflow: 'hidden', pb: 1, minHeight: 0 }}>
                    <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                      <Typography variant="h6" component="h2" noWrap sx={{ maxWidth: '70%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {invoice.invoice_number || 'No Number'}
                      </Typography>
                    </Box>
                    <Box display="flex" gap={1} mb={1}>
                      <Chip
                        label={invoice.status || 'unknown'}
                        color={getStatusColor(invoice.status)}
                        size="small"
                        sx={{ maxWidth: '50%', overflow: 'hidden', textOverflow: 'ellipsis' }}
                      />
                      <Chip
                        label={invoice.method || 'unknown'}
                        color={getMethodColor(invoice.method)}
                        size="small"
                        sx={{ maxWidth: '50%', overflow: 'hidden', textOverflow: 'ellipsis' }}
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary" noWrap mb={1} sx={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {invoice.supplier_name || 'Unknown Supplier'}
                    </Typography>
                    <Box sx={{ mt: 'auto' }}>
                      {invoice.invoice_total && (
                        <Typography variant="h6" color="primary" noWrap>
                          ${parseFloat(invoice.invoice_total).toFixed(2)}
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleViewInvoice}>
          <ListItemIcon>
            <VisibilityIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>View</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleEditInvoice}>
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDeleteClick}>
          <ListItemIcon>
            <DeleteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => { setDeleteDialogOpen(false); setSelectedInvoice(null); }}>
        <DialogTitle>Delete Invoice</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete invoice "{selectedInvoice?.invoice_number}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDeleteDialogOpen(false); setSelectedInvoice(null); }}>Cancel</Button>
          <Button onClick={async () => { await handleDeleteConfirm(); setSelectedInvoice(null); }} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Dashboard; 