import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  MenuItem,
  IconButton,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import axios from 'axios';

const OrderForm = ({ orderId }) => {
  const [order, setOrder] = useState({
    customerName: '',
    orderDate: new Date().toISOString().split('T')[0],
    status: 'pending',
    items: [],
    total: 0
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (orderId) {
      fetchOrder();
    }
  }, [orderId]);

  const fetchOrder = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/orders/${orderId}`);
      setOrder(response.data);
    } catch (error) {
      console.error('Error fetching order:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (orderId) {
        await axios.put(`/api/orders/${orderId}`, order);
      } else {
        await axios.post('/api/orders', order);
      }
      // Implementar navegación de regreso a la lista
    } catch (error) {
      console.error('Error saving order:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddItem = () => {
    setOrder({
      ...order,
      items: [...order.items, { productId: '', quantity: 1, price: 0 }]
    });
  };

  const handleRemoveItem = (index) => {
    const newItems = order.items.filter((_, i) => i !== index);
    setOrder({ ...order, items: newItems });
  };

  const handleItemChange = (index, field, value) => {
    const newItems = [...order.items];
    newItems[index] = { ...newItems[index], [field]: value };
    setOrder({ ...order, items: newItems });
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          {orderId ? 'Editar Pedido' : 'Nuevo Pedido'}
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6}>
            <TextField
              required
              fullWidth
              label="Cliente"
              value={order.customerName}
              onChange={(e) => setOrder({ ...order, customerName: e.target.value })}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              required
              fullWidth
              type="date"
              label="Fecha"
              value={order.orderDate}
              onChange={(e) => setOrder({ ...order, orderDate: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              select
              required
              fullWidth
              label="Estado"
              value={order.status}
              onChange={(e) => setOrder({ ...order, status: e.target.value })}
            >
              <MenuItem value="pending">Pendiente</MenuItem>
              <MenuItem value="processing">En Proceso</MenuItem>
              <MenuItem value="completed">Completado</MenuItem>
              <MenuItem value="cancelled">Cancelado</MenuItem>
            </TextField>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Items del Pedido
          </Typography>
          {order.items.map((item, index) => (
            <Grid container spacing={2} key={index} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={4}>
                <TextField
                  required
                  fullWidth
                  label="Producto"
                  value={item.productId}
                  onChange={(e) => handleItemChange(index, 'productId', e.target.value)}
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  required
                  fullWidth
                  type="number"
                  label="Cantidad"
                  value={item.quantity}
                  onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  required
                  fullWidth
                  type="number"
                  label="Precio"
                  value={item.price}
                  onChange={(e) => handleItemChange(index, 'price', e.target.value)}
                />
              </Grid>
              <Grid item xs={12} sm={2}>
                <IconButton color="error" onClick={() => handleRemoveItem(index)}>
                  <DeleteIcon />
                </IconButton>
              </Grid>
            </Grid>
          ))}
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleAddItem}
            sx={{ mt: 2 }}
          >
            Agregar Item
          </Button>
        </Box>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
          >
            {orderId ? 'Actualizar' : 'Crear'} Pedido
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default OrderForm;
