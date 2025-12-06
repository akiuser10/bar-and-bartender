# AI-Powered Product Categorization Setup

The system now includes AI-powered automatic categorization for products during bulk upload. When uploading products via Excel, if a product's category or sub-category is missing or set to "Other", the system will automatically use AI to identify the correct category and sub-category based on the product description.

## How It Works

1. **During Bulk Upload**: When you upload products via Excel
2. **Automatic Detection**: If category is missing/empty/"Other" OR sub-category is missing/empty/"Other"
3. **AI Analysis**: The system analyzes the product description (and supplier if available)
4. **Smart Categorization**: AI identifies the most appropriate category and sub-category from your available options
5. **Automatic Assignment**: The identified values are automatically assigned to the product

## Setup Instructions

### Step 1: Get an OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Click **"Create new secret key"**
5. Copy the API key (you won't be able to see it again!)

### Step 2: Add API Key to Railway

1. Go to your Railway project dashboard
2. Click on your service
3. Go to **Variables** tab
4. Click **"New Variable"**
5. Add:
   - **Name**: `OPENAI_API_KEY`
   - **Value**: Your OpenAI API key (paste the key you copied)
6. Click **"Add"**

### Step 3: Redeploy

Railway will automatically redeploy your application when you add the environment variable. Wait 1-2 minutes for the deployment to complete.

## Features

- **Automatic**: Works seamlessly during bulk upload
- **Smart**: Uses product description and supplier context
- **Safe**: Only categorizes when category/sub-category is missing or "Other"
- **Graceful**: If AI fails or API key is not configured, uses original values
- **Validated**: Ensures AI responses match your valid categories and sub-categories

## Cost Considerations

- Uses OpenAI's GPT-3.5-turbo model (cost-effective)
- Only called when needed (missing/Other categories)
- Each categorization costs approximately $0.0001-0.0002
- For 1000 products needing categorization: ~$0.10-0.20

## Disabling AI Categorization

If you want to disable AI categorization:
- Simply don't set the `OPENAI_API_KEY` environment variable
- The system will work normally without AI, using the values from your Excel file

## Troubleshooting

**AI not categorizing products:**
- Check that `OPENAI_API_KEY` is set in Railway environment variables
- Check Railway logs for any API errors
- Ensure your OpenAI account has credits available

**Incorrect categorizations:**
- The AI uses your exact category and sub-category lists
- If a product is miscategorized, you can edit it manually after upload
- The AI learns from context, so more descriptive product names work better
