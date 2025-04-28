# CIT610_ColdStartLatency

Setting Up a Cold Start Latency Testing Environment
Here's a comprehensive step-by-step guide to build a testing environment for measuring cold start latency across serverless platforms:
1. Development Environment Setup
bash# Create a project directory
mkdir cold-start-testing
cd cold-start-testing

# Initialize git repository
git init

# Create a basic project structure
mkdir -p aws/functions azure/functions benchmarks/results
touch README.md
2. Install Required Tools
bash# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Serverless Framework for easier deployments
npm install -g serverless

# Install other dependencies
npm init -y
npm install --save-dev aws-sdk @azure/functions axios chart.js jest moment
3. Configure Cloud Provider Credentials
bash# Configure AWS credentials
aws configure
# Enter your AWS Access Key, Secret Key, and preferred region

# Login to Azure
az login
4. Create Test Functions for AWS
Create a basic serverless.yml file:
yaml# aws/serverless.yml
service: cold-start-benchmark

provider:
  name: aws
  runtime: nodejs16.x
  region: us-east-1

functions:
  minimal:
    handler: functions/minimal.handler
    memorySize: 128
    
  withDependencies:
    handler: functions/withDependencies.handler
    memorySize: 128
    
  databaseAccess:
    handler: functions/databaseAccess.handler
    memorySize: 512
    environment:
      DB_HOST: ${env:DB_HOST}
      DB_USER: ${env:DB_USER}
      DB_PASSWORD: ${env:DB_PASSWORD}
Create test functions with instrumentation:
javascript// aws/functions/minimal.js
let coldStart = true;

exports.handler = async (event) => {
  const startTime = Date.now();
  
  // Record if this is a cold start
  const isColdStart = coldStart;
  coldStart = false;
  
  // Simulate minimal processing
  const result = { message: "Hello from minimal function" };
  
  const endTime = Date.now();
  const duration = endTime - startTime;
  
  return {
    statusCode: 200,
    body: JSON.stringify({
      result,
      timing: {
        coldStart: isColdStart,
        duration,
        timestamp: new Date().toISOString()
      }
    })
  };
};
5. Create Test Functions for Azure
Create a function app:
bashcd azure
func init FunctionApp --javascript
cd FunctionApp
func new --name coldStartTest --template "HTTP trigger"
Modify the function to include timing:
javascript// azure/FunctionApp/coldStartTest/index.js
let coldStart = true;

module.exports = async function (context, req) {
  const startTime = Date.now();
  
  // Record if this is a cold start
  const isColdStart = coldStart;
  coldStart = false;
  
  // Simulate minimal processing
  const response = {
    result: { message: "Hello from Azure function" },
    timing: {
      coldStart: isColdStart,
      duration: Date.now() - startTime,
      timestamp: new Date().toISOString()
    }
  };
  
  context.res = {
    status: 200,
    body: response
  };
};
6. Create Benchmark Test Script
javascript// benchmarks/run-tests.js
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const moment = require('moment');

// Configuration
const CONFIG = {
  iterations: 50,
  cooldownMinutes: 10,  // Time between test runs to ensure cold starts
  endpoints: {
    aws: {
      minimal: process.env.AWS_MINIMAL_ENDPOINT,
      withDependencies: process.env.AWS_DEPENDENCIES_ENDPOINT,
      databaseAccess: process.env.AWS_DATABASE_ENDPOINT
    },
    azure: {
      minimal: process.env.AZURE_MINIMAL_ENDPOINT
    }
  }
};

// Create results directory with timestamp
const resultDir = path.join(
  __dirname, 
  'results', 
  `run-${moment().format('YYYY-MM-DD-HH-mm-ss')}`
);
fs.mkdirSync(resultDir, { recursive: true });

async function runTest(name, url) {
  console.log(`Running test for ${name}`);
  
  const results = [];
  
  for (let i = 0; i < CONFIG.iterations; i++) {
    try {
      // First request will trigger cold start
      console.log(`  Iteration ${i+1}/${CONFIG.iterations}`);
      const start = Date.now();
      const response = await axios.get(url);
      const end = Date.now();
      
      // Record client-side latency too
      results.push({
        iteration: i,
        clientLatency: end - start,
        serverTiming: response.data.timing,
        timestamp: new Date().toISOString()
      });
      
      // Wait for cooldown to ensure next test is cold
      if (i < CONFIG.iterations - 1) {
        console.log(`  Waiting ${CONFIG.cooldownMinutes} minutes for cold start...`);
        await new Promise(resolve => 
          setTimeout(resolve, CONFIG.cooldownMinutes * 60 * 1000)
        );
      }
    } catch (error) {
      console.error(`Error in test ${name}, iteration ${i}:`, error);
      results.push({
        iteration: i,
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  // Save results
  fs.writeFileSync(
    path.join(resultDir, `${name}.json`),
    JSON.stringify(results, null, 2)
  );
  
  return results;
}

async function runAllTests() {
  const allResults = {};
  
  // Run AWS tests
  for (const [name, url] of Object.entries(CONFIG.endpoints.aws)) {
    allResults[`aws_${name}`] = await runTest(`aws_${name}`, url);
  }
  
  // Run Azure tests
  for (const [name, url] of Object.entries(CONFIG.endpoints.azure)) {
    allResults[`azure_${name}`] = await runTest(`azure_${name}`, url);
  }
  
  // Save consolidated results
  fs.writeFileSync(
    path.join(resultDir, 'all-results.json'),
    JSON.stringify(allResults, null, 2)
  );
  
  // Generate summary
  generateSummary(allResults, resultDir);
}

function generateSummary(results, dir) {
  const summary = {};
  
  for (const [name, testResults] of Object.entries(results)) {
    const coldStarts = testResults.filter(r => 
      r.serverTiming && r.serverTiming.coldStart
    );
    
    const warmStarts = testResults.filter(r => 
      r.serverTiming && !r.serverTiming.coldStart
    );
    
    summary[name] = {
      totalRuns: testResults.length,
      errors: testResults.filter(r => r.error).length,
      coldStarts: {
        count: coldStarts.length,
        avgClientLatency: average(coldStarts.map(r => r.clientLatency)),
        avgServerDuration: average(coldStarts.map(r => r.serverTiming?.duration)),
        p95ClientLatency: percentile(coldStarts.map(r => r.clientLatency), 95),
        p95ServerDuration: percentile(coldStarts.map(r => r.serverTiming?.duration), 95)
      },
      warmStarts: {
        count: warmStarts.length,
        avgClientLatency: average(warmStarts.map(r => r.clientLatency)),
        avgServerDuration: average(warmStarts.map(r => r.serverTiming?.duration)),
        p95ClientLatency: percentile(warmStarts.map(r => r.clientLatency), 95),
        p95ServerDuration: percentile(warmStarts.map(r => r.serverTiming?.duration), 95)
      }
    };
  }
  
  fs.writeFileSync(
    path.join(dir, 'summary.json'),
    JSON.stringify(summary, null, 2)
  );
  
  console.log('Summary:', summary);
}

// Helper functions
function average(arr) {
  if (!arr.length) return 0;
  return arr.reduce((sum, val) => sum + val, 0) / arr.length;
}

function percentile(arr, p) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * p / 100;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
}

// Run the tests
runAllTests()
  .then(() => console.log('All tests completed'))
  .catch(err => console.error('Error running tests:', err));
7. Create Visualization Script
javascript// benchmarks/visualize.js
const fs = require('fs');
const path = require('path');
const { createCanvas } = require('canvas');

// Get latest results directory
const resultsDir = path.join(__dirname, 'results');
const dirs = fs.readdirSync(resultsDir).filter(f => 
  fs.statSync(path.join(resultsDir, f)).isDirectory()
);
const latestDir = path.join(resultsDir, dirs.sort().pop());

// Load summary
const summary = JSON.parse(fs.readFileSync(
  path.join(latestDir, 'summary.json'), 
  'utf8'
));

// Create comparison chart
function createComparisonChart() {
  const canvas = createCanvas(800, 600);
  const ctx = canvas.getContext('2d');
  
  // Draw chart
  // (This is simplified - in a real implementation you would use Chart.js or D3.js)
  
  // Save chart
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(path.join(latestDir, 'comparison.png'), buffer);
}

createComparisonChart();
console.log(`Visualization saved to ${latestDir}`);
8. Deploy Your Functions
bash# Deploy AWS functions
cd aws
serverless deploy

# Deploy Azure functions
cd ../azure/FunctionApp
func azure functionapp publish YourAzureFunctionAppName
9. Configure Environment Variables
Create a .env file with your function endpoints:
# .env
AWS_MINIMAL_ENDPOINT=https://xxxx.execute-api.us-east-1.amazonaws.com/dev/minimal
AWS_DEPENDENCIES_ENDPOINT=https://xxxx.execute-api.us-east-1.amazonaws.com/dev/withDependencies
AWS_DATABASE_ENDPOINT=https://xxxx.execute-api.us-east-1.amazonaws.com/dev/databaseAccess
AZURE_MINIMAL_ENDPOINT=https://your-azure-function.azurewebsites.net/api/coldStartTest
10. Run Benchmark Tests
bash# Install dotenv for environment variables
npm install dotenv

# Add to beginning of run-tests.js:
require('dotenv').config();

# Run the tests
node benchmarks/run-tests.js
11. Analyze Results
bash# Generate visualizations
node benchmarks/visualize.js

# View the summary
cat benchmarks/results/[latest-directory]/summary.json
12. Optional: Create CI/CD Pipeline
Create a GitHub Actions workflow file for automated testing:
yaml# .github/workflows/benchmark.yml
name: Cold Start Benchmarks

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sundays
  workflow_dispatch:  # Manual trigger

jobs:
  benchmark:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '16'
        
    - name: Install dependencies
      run: npm ci
      
    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
        
    - name: Configure Azure
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
        
    - name: Run benchmarks
      run: node benchmarks/run-tests.js
      env:
        AWS_MINIMAL_ENDPOINT: ${{ secrets.AWS_MINIMAL_ENDPOINT }}
        AWS_DEPENDENCIES_ENDPOINT: ${{ secrets.AWS_DEPENDENCIES_ENDPOINT }}
        AWS_DATABASE_ENDPOINT: ${{ secrets.AWS_DATABASE_ENDPOINT }}
        AZURE_MINIMAL_ENDPOINT: ${{ secrets.AZURE_MINIMAL_ENDPOINT }}
        
    - name: Generate visualizations
      run: node benchmarks/visualize.js
      
    - name: Upload results
      uses: actions/upload-artifact@v2
      with:
        name: benchmark-results
        path: benchmarks/results/
13. Extensions for More Advanced Testing
For more comprehensive testing, you might want to add:

Different memory configurations:

Modify your serverless.yml to create multiple variants with different memory settings


Package size variations:

Create functions with different dependency weights


Region testing:

Deploy to multiple regions and compare results


Concurrent cold starts:

Modify the test script to trigger multiple cold starts simultaneously