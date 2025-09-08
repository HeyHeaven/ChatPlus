#!/bin/bash
# Database setup script for Enterprise WhatsApp Chat Analyzer

echo "Setting up PostgreSQL database..."

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running. Please start PostgreSQL first."
    exit 1
fi

# Create database
echo "Creating database 'whatsapp_analyzer'..."
createdb whatsapp_analyzer

# Create user (optional)
echo "Creating user 'wca_user'..."
createuser --interactive wca_user

echo "✅ Database setup complete!"
echo "Please update the configuration file with your database credentials."
