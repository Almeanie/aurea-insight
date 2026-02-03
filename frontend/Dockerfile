FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build-time API URL (required for production; baked into client bundle)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Production build
RUN npm run build

# Expose port (Cloud Run sets PORT, often 8080)
EXPOSE 8080
ENV PORT=8080

# Run production server
CMD ["npm", "start"]
