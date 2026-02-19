Here's a step-by-step guide for setting up your project with **ShadCN UI** and **Prisma** with **MongoDB**, using **Bun** as your package manager:

---

### **1. Install ShadCN UI**
ShadCN UI simplifies your React/Next.js development by providing pre-built components.

#### Installation Steps:
1. **Initialize the ShadCN UI setup:**
   ```bash
   bunx create-shadcn-ui
   ```
2. **Follow the interactive prompts** to customize the setup:
   - Choose the components you want to install.
   - Configure any theme settings.

3. **Integrate ShadCN UI into your project:**
   After installation, ensure you import and use the components as needed in your Next.js app. For example:
   ```tsx
   import { Button } from '@/components/ui/button';

   export default function Home() {
     return <Button>Click Me</Button>;
   }
   ```

---

### **2. Install Prisma with MongoDB**
Prisma provides a type-safe ORM for working with your MongoDB database.

#### Installation Steps:
1. **Add Prisma and the Prisma CLI:**
   ```bash
   bun add prisma @prisma/client
   bunx prisma init
   ```

2. **Configure Prisma for MongoDB:**
   Update your `prisma/schema.prisma` file:
   ```prisma
   datasource db {
     provider = "mongodb"
     url      = env("DATABASE_URL")
   }

   generator client {
     provider = "prisma-client-js"
   }

   model User {
     id    String @id @default(auto()) @map("_id") @db.ObjectId
     name  String
     email String @unique
   }
   ```

3. **Set the Database URL:**
   Add the MongoDB connection string in your `.env` file:
   ```env
   DATABASE_URL="mongodb+srv://<username>:<password>@cluster0.mongodb.net/<database>?retryWrites=true&w=majority"
   ```

4. **Generate the Prisma client:**
   ```bash
   bunx prisma generate
   ```

5. **Apply database migrations:**
   Since MongoDB is schema-less, migrations might not always apply. Instead, you can validate your schema with:
   ```bash
   bunx prisma db push
   ```

---

### **3. Connect Prisma to Your Next.js App**
To fetch data using Prisma in your Next.js app:

1. **Import and initialize the Prisma client:**
   ```tsx
   import { PrismaClient } from '@prisma/client';

   const prisma = new PrismaClient();

   export default async function handler(req, res) {
     const users = await prisma.user.findMany();
     res.json(users);
   }
   ```

2. **Use API routes or server components** for data fetching.

---

### **4. Run the Development Server**
Start your app with:
```bash
bun dev
```

Visit [http://localhost:3000](http://localhost:3000) to see your Next.js app running with ShadCN UI and MongoDB integration.

---

### **5. Deployment**
Deploy your app on [Vercel](https://vercel.com) and configure your environment variables (e.g., `DATABASE_URL`) in the Vercel dashboard.

For more details:
- [Prisma MongoDB Documentation](https://www.prisma.io/docs/guides/database-connectors/mongodb)
- [ShadCN UI Documentation](https://shadcn.dev/docs)

