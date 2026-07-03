FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY frontend/package*.json ./
RUN npm install

# Copy application files
COPY frontend/ .

EXPOSE 5173

# Run the Vite server exposing it to all network interfaces
CMD ["npm", "run", "dev", "--", "--host"]
