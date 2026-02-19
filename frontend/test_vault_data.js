const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const PROJECT_ID = "cmh0pxnxm0005ofnlntnlpvku";

async function testVaultData() {
  try {
    const vault = await prisma.vault.findUnique({
      where: { projectId: PROJECT_ID },
      include: {
        Folders: {
          orderBy: { path: 'asc' }
        },
        Documents: {
          include: { Folder: true },
          orderBy: { uploadedAt: 'desc' }
        }
      }
    });
    
    if (!vault) {
      console.log("❌ No vault found");
      return;
    }
    
    console.log(`\n✅ Vault: ${vault.id}`);
    console.log(`   Name: ${vault.name}`);
    console.log(`   Project ID: ${vault.projectId}`);
    console.log(`\n📁 Folders (${vault.Folders.length}):`);
    vault.Folders.forEach(f => {
      console.log(`   ${f.path}`);
    });
    
    console.log(`\n📄 Documents (${vault.Documents.length}):`);
    const byFolder = {};
    vault.Documents.forEach(d => {
      const folderPath = d.Folder?.path || 'Root';
      if (!byFolder[folderPath]) byFolder[folderPath] = [];
      byFolder[folderPath].push(d.originalName);
    });
    
    Object.entries(byFolder).forEach(([folder, docs]) => {
      console.log(`\n   ${folder}:`);
      docs.forEach(doc => console.log(`      - ${doc}`));
    });
    
  } catch (error) {
    console.error("Error:", error);
  } finally {
    await prisma.$disconnect();
  }
}

testVaultData();
