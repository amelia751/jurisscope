const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

const prisma = new PrismaClient();

const PROJECT_ID = "cmh0pxnxm0005ofnlntnlpvku";
const DEMO_CASE_PATH = "/Users/anhlam/Downloads/demo-case";

async function populateVault() {
  try {
    console.log("🔍 Starting vault population...");
    
    // Get or create vault
    let vault = await prisma.vault.findUnique({
      where: { projectId: PROJECT_ID }
    });
    
    if (!vault) {
      vault = await prisma.vault.create({
        data: {
          projectId: PROJECT_ID,
          name: "Evidence"
        }
      });
      console.log(`✅ Created vault: ${vault.id}`);
    } else {
      console.log(`✅ Found existing vault: ${vault.id}`);
    }
    
    // Define the folder structure manually based on demo-case
    const folderStructure = [
      { name: "demo-case", path: "/demo-case", depth: 0 },
      { name: "regulations", path: "/demo-case/regulations", depth: 1 },
      { name: "internal_docs", path: "/demo-case/internal_docs", depth: 1 },
      { name: "legal_correspondence", path: "/demo-case/legal_correspondence", depth: 1 },
      { name: "case_summaries", path: "/demo-case/case_summaries", depth: 1 },
    ];
    
    const files = {
      "/demo-case/regulations": [
        "AI_Act_Final.pdf",
        "GDPR_Regulation_2016_679.pdf",
        "Digital_Markets_Act.pdf"
      ],
      "/demo-case/internal_docs": [
        "TechNova_AI_Compliance_Report.pdf",
        "Data_Processing_Agreement.pdf",
        "Risk_Assessment_Memo.pdf",
        "Product_Specs_AI_Model.pdf"
      ],
      "/demo-case/legal_correspondence": [
        "DataSure_Complaint_Letter.pdf",
        "Mediation_Settlement_Draft.pdf",
        "TechNova_Response_Letter.pdf"
      ],
      "/demo-case/case_summaries": [
        "Court_Filing_Summary.pdf",
        "Legal_Opinion_Memo.pdf"
      ]
    };
    
    console.log(`\n📊 Creating folder structure...`);
    
    const folderMap = new Map();
    
    // Create folders
    for (const folderInfo of folderStructure) {
      try {
        let dbFolder = await prisma.folder.findFirst({
          where: {
            vaultId: vault.id,
            path: folderInfo.path
          }
        });
        
        if (!dbFolder) {
          dbFolder = await prisma.folder.create({
            data: {
              vaultId: vault.id,
              name: folderInfo.name,
              path: folderInfo.path,
              depth: folderInfo.depth
            }
          });
          console.log(`   ✅ Created folder: ${folderInfo.path}`);
        } else {
          console.log(`   ℹ️  Folder exists: ${folderInfo.path}`);
        }
        
        folderMap.set(folderInfo.path, dbFolder);
      } catch (error) {
        console.error(`   ❌ Error creating folder ${folderInfo.path}:`, error.message);
      }
    }
    
    console.log(`\n📄 Creating documents...`);
    
    // Create documents
    for (const [folderPath, fileList] of Object.entries(files)) {
      const folder = folderMap.get(folderPath);
      if (!folder) {
        console.log(`   ⚠️  Folder not found: ${folderPath}`);
        continue;
      }
      
      console.log(`\n   Folder: ${folderPath}`);
      
      for (const fileName of fileList) {
        try {
          const existingDoc = await prisma.document.findFirst({
            where: {
              vaultId: vault.id,
              originalName: fileName
            }
          });
          
          if (!existingDoc) {
            // Get actual file size from demo-case
            const relativePath = folderPath.replace('/demo-case/', '');
            const filePath = path.join(DEMO_CASE_PATH, relativePath, fileName);
            let fileSize = 1000000; // default 1MB
            try {
              const stats = fs.statSync(filePath);
              fileSize = stats.size;
            } catch (e) {
              console.log(`     ⚠️  Could not stat file: ${fileName}`);
            }
            
            const gcsPath = `${PROJECT_ID}${folderPath.replace('/demo-case', '')}/${fileName}`;
            
            await prisma.document.create({
              data: {
                vaultId: vault.id,
                folderId: folder.id,
                name: fileName.replace('.pdf', ''),
                originalName: fileName,
                gcsPath: gcsPath,
                gcsBucket: "clause-raw-475719",
                mimeType: "application/pdf",
                size: BigInt(fileSize),
                status: "completed"
              }
            });
            console.log(`      ✅ Created: ${fileName}`);
          } else {
            console.log(`      ℹ️  Exists: ${fileName}`);
          }
        } catch (error) {
          console.error(`      ❌ Error with ${fileName}:`, error.message);
        }
      }
    }
    
    // Final count
    const finalFolders = await prisma.folder.count({ where: { vaultId: vault.id } });
    const finalDocs = await prisma.document.count({ where: { vaultId: vault.id } });
    
    console.log(`\n✨ Complete!`);
    console.log(`   Folders in database: ${finalFolders}`);
    console.log(`   Documents in database: ${finalDocs}`);
    
  } catch (error) {
    console.error("❌ Error:", error);
    console.error(error.stack);
  } finally {
    await prisma.$disconnect();
  }
}

populateVault();
