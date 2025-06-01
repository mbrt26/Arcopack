import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import axios from 'axios';

const OrderList = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);

  const columns = [
    { field: 'id', headerName: 'ID', width: 90 },
    { field: 'orderDate', headerName: 'Fecha', width: 130 },
    { field: 'customerName', headerName: 'Cliente', width: 200 },
    { field: 'total', headerName: 'Total', width: 130, type: 'number' },
    { field: 'status', headerName: 'Estado', width: 130 },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 130,
      renderCell: (params) => (
        <Box>
          <IconButton color="primary" onClick={() => handleEdit(params.row.id)}>
            <EditIcon />
          </IconButton>
          <IconButton color="error" onClick={() => handleDelete(params.row.id)}>
            <DeleteIcon />
          </IconButton>
        </Box>
      ),
    },
  ];

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/orders');
      setOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (id) => {
    // Implementar navegación a la página de edición
    console.log('Edit order:', id);
  };

  const handleDelete = async (id) => {
    if (window.confirm('¿Está seguro de eliminar este pedido?')) {
      try {
        await axios.delete(`/api/orders/${id}`);
        fetchOrders();
      } catch (error) {
        console.error('Error deleting order:', error);
      }
    }
  };

  const handleCreate = () => {
    // Implementar navegación a la página de creación
    console.log('Create new order');
  };

  return (
    <Box sx={{ height: 400, width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5" component="h2">
          Pedidos
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreate}
        >
          Nuevo Pedido
        </Button>
      </Box>
      <Paper sx={{ height: '100%', width: '100%' }}>
        <DataGrid
          rows={orders}
          columns={columns}
          pageSize={5}
          rowsPerPageOptions={[5]}
          checkboxSelection
          disableSelectionOnClick
          loading={loading}
        />
      </Paper>
    </Box>
  );
};

export default OrderList;
