#!/usr/bin/env python3
"""
Generate a secure SECRET_KEY for Flask application
Run this script to generate a random secret key for production use
"""
import secrets

if __name__ == '__main__':
    secret_key = secrets.token_hex(32)
    print("\n" + "="*60)
    print("Generated SECRET_KEY for your Flask application:")
    print("="*60)
    print(secret_key)
    print("="*60)
    print("\nCopy this value and use it as your SECRET_KEY environment variable")
    print("in your hosting platform (Render, Railway, etc.)\n")
