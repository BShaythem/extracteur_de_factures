import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Container,
  Typography,
  Button,
  Box,
  Paper,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  ArrowBack as ArrowBackIcon,
  PlayArrow as PlayArrowIcon,
} from '@mui/icons-material';
import api from '../services/api';

const Extraction = () => {
  const [files, setFiles] = useState([]);
  const [method, setMethod] = useState('layoutlmv3');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(acceptedFiles);
    setError('');
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.bmp'],
      'application/pdf': ['.pdf'],
    },
    multiple: false,
  });

  const handleExtract = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', files[0]);

      // Map methods to dedicated backend endpoints
      const endpointMap = {
        layoutlmv3: '/layoutlmv3/extract_layoutlmv3',
        groq: '/groq/extract_llm_groq',
        ollama: '/ollama/extract_llm_ollama',
      };

      const endpoint = endpointMap[method];
      if (!endpoint) {
        setError('Invalid extraction method selected');
        setLoading(false);
        return;
      }

      const response = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Navigate to results page with the extracted data
      navigate('/results', {
        state: {
          extractedData: response.data,
          files: files,
          method: method,
        },
      });
    } catch (error) {
      setError(error.response?.data?.error || 'Extraction failed');
    } finally {
      setLoading(false);
    }
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" alignItems="center" mb={4}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/')}
          sx={{ mr: 2 }}
        >
          Back to Dashboard
        </Button>
        <Typography variant="h4" component="h1">
          Extract Invoice Data
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* File Upload Section */}
        <Grid item xs={12} md={6}>
          <Paper
            {...getRootProps()}
            sx={{
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              border: '2px dashed',
              borderColor: isDragActive ? 'primary.main' : 'grey.300',
              backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
              transition: 'all 0.2s ease',
              '&:hover': {
                borderColor: 'primary.main',
                backgroundColor: 'action.hover',
              },
            }}
          >
            <input {...getInputProps()} />
            <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              or click to select a file
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Supports: JPG, PNG, GIF, BMP, PDF
            </Typography>
          </Paper>
        </Grid>

        {/* Method Selection */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Extraction Method
            </Typography>
            <FormControl component="fieldset">
              <FormLabel component="legend">Choose the extraction method:</FormLabel>
              <RadioGroup
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                <FormControlLabel
                  value="layoutlmv3"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="body1">LayoutLMv3</Typography>
                      <Typography variant="caption" color="text.secondary">
                        AI model trained on document layout understanding
                      </Typography>
                    </Box>
                  }
                />
                <FormControlLabel
                  value="groq"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="body1">LLM (Groq)</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Cloud-based LLM extraction via Groq API
                      </Typography>
                    </Box>
                  }
                />
                <FormControlLabel
                  value="ollama"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="body1">LLM (Ollama)</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Local LLM extraction via Ollama
                      </Typography>
                    </Box>
                  }
                />
              </RadioGroup>
            </FormControl>
          </Paper>
        </Grid>
      </Grid>

      {/* Selected Files */}
      {files.length > 0 && (
        <Box mt={3}>
          <Typography variant="h6" gutterBottom>
            Selected File
          </Typography>
          <Grid container spacing={2}>
            {files.map((file, index) => (
              <Grid item xs={12} key={index}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="body2" noWrap>
                          {file.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatFileSize(file.size)}
                        </Typography>
                      </Box>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => removeFile(index)}
                      >
                        Remove
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Extract Button */}
      <Box mt={4} textAlign="center">
        <Button
          variant="contained"
          size="large"
          startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
          onClick={handleExtract}
          disabled={loading || files.length === 0}
          sx={{ minWidth: 200 }}
        >
          {loading ? 'Extracting...' : 'Start Extraction'}
        </Button>
      </Box>
    </Container>
  );
};

export default Extraction; 