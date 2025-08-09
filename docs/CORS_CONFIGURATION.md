# CORS Configuration Guide

## Overview
The AI Reception System implements environment-based CORS (Cross-Origin Resource Sharing) configuration to secure API access in production while allowing flexible development.

## Configuration

### Development Environment
- **Environment**: `ENVIRONMENT=development`
- **CORS Policy**: Allows all origins (`*`)
- **Credentials**: Disabled when allowing all origins
- **Purpose**: Easier local development and testing

### Production Environment
- **Environment**: `ENVIRONMENT=production`
- **CORS Policy**: Restricts to specific domains
- **Credentials**: Enabled for specific origins
- **Configuration**: Via `ALLOWED_ORIGINS` environment variable

## Environment Variables

### Backend (.env)
```bash
# Development
ENVIRONMENT=development
ALLOWED_ORIGINS=  # Empty or omitted for development

# Production
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://your-domain.com
```

### Vercel Deployment
Set the following environment variables in Vercel dashboard:
- `ENVIRONMENT`: Set to `production`
- `ALLOWED_ORIGINS`: Comma-separated list of allowed frontend domains

Example:
```
ALLOWED_ORIGINS=https://your-app.vercel.app,https://app.example.com
```

## Implementation Details

### Backend (FastAPI)
- **config.py**: Dynamic CORS configuration based on environment
  - Development: Returns `["*"]` for all origins
  - Production: Parses `ALLOWED_ORIGINS` environment variable
- **main.py**: Applies CORS middleware with environment-specific settings

### Frontend
- Uses `NEXT_PUBLIC_API_URL` to configure backend API endpoint
- Default: `http://localhost:8000` for development
- Production: Set to your deployed backend URL

## Testing CORS

### Test Development Mode
```bash
# Should allow any origin
curl -X OPTIONS http://localhost:8000/api/health \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" -i
```

### Test Production Mode
```bash
# Set production environment
export ENVIRONMENT=production
export ALLOWED_ORIGINS=https://your-app.vercel.app

# Should only allow specified origin
curl -X OPTIONS http://your-api.com/api/health \
  -H "Origin: https://your-app.vercel.app" \
  -H "Access-Control-Request-Method: GET" -i
```

## Security Considerations

1. **Never use `*` in production** - Always specify exact allowed origins
2. **Use HTTPS** - Ensure all production domains use HTTPS
3. **Keep origins minimal** - Only allow necessary domains
4. **Regular audits** - Review and update allowed origins periodically

## Troubleshooting

### CORS errors in browser console
1. Check if the origin is in `ALLOWED_ORIGINS`
2. Verify `ENVIRONMENT` is set correctly
3. Ensure backend is restarted after config changes

### Development CORS issues
1. Confirm `ENVIRONMENT=development` in backend `.env`
2. Check no `ALLOWED_ORIGINS` is set (or it's empty)
3. Restart backend server

### Production CORS issues
1. Verify `ALLOWED_ORIGINS` includes your frontend domain
2. Check domain matches exactly (including protocol)
3. Ensure no trailing slashes in origins

## Example Configurations

### Local Development
```bash
# Backend .env
ENVIRONMENT=development
# No ALLOWED_ORIGINS needed
```

### Staging Environment
```bash
# Backend .env
ENVIRONMENT=production
ALLOWED_ORIGINS=https://staging.example.com
```

### Production with Multiple Frontends
```bash
# Backend .env
ENVIRONMENT=production
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com,https://mobile.example.com
```