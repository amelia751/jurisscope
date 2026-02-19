"use server";
import { client } from "@/lib/prisma";

// Hardcoded user for hackathon (no Clerk auth needed)
const HARDCODED_USER = {
  id: "hackathon-user-001",
  clerkId: "hackathon-user-001",
  name: "JurisScope User",
  email: "user@jurisscope.dev",
  profileImage: null,
};

/**
 * Authenticate user - returns hardcoded user for hackathon.
 * Maintains compatibility with original interface for easy auth re-addition later.
 */
export const onAuthenticateUser = async () => {
  try {
    // Use upsert to handle race conditions
    const user = await client.user.upsert({
      where: {
        clerkId: HARDCODED_USER.clerkId,
      },
      update: {}, // Don't update anything if exists
      create: {
        clerkId: HARDCODED_USER.clerkId,
        email: HARDCODED_USER.email,
        name: HARDCODED_USER.name,
        profileImage: HARDCODED_USER.profileImage,
      },
      include: {
        Projects: {
          select: {
            id: true,
            title: true,
            description: true,
          },
        },
      },
    });

    return { status: 200, user };
  } catch (error) {
    console.log("🔴 ERROR in onAuthenticateUser:", error);
    // Return hardcoded user even if DB fails (for development)
    return { 
      status: 200, 
      user: {
        ...HARDCODED_USER,
        createdAt: new Date(),
        updatedAt: new Date(),
        Projects: [],
      }
    };
  }
};

/**
 * Get user by ID
 */
export const getUser = async (userId: string) => {
  try {
    const userExist = await client.user.findUnique({
      where: {
        id: userId,
      },
    });
    if (userExist) {
      return { status: 200, user: userExist };
    }
    // Fallback to hardcoded user
    return { status: 200, user: HARDCODED_USER };
  } catch (error) {
    console.log("🔴 ERROR in getUser:", error);
    return { status: 200, user: HARDCODED_USER };
  }
};

/**
 * Get current user (hardcoded for hackathon)
 */
export const getCurrentUser = async () => {
  return onAuthenticateUser();
};
