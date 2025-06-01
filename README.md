Preparation steps for deployment:
1. Authenticate doctl for use with your DigitalOcean account:
   ```bash
   doctl auth init -t <TOKEN>
   ```
2. Connect local serverless support to a functions namespace:
   ```bash
   doctl serverless connect
   ```

To deploy:
1. Copy [`.env.example`](.env.example) and save it as `.env`
2. Fill the `.env` file
3. Run from the project's root:
   ```bash
   doctl serverless deploy ../SciPulse --remote-build
   ```
