"use server";
import { ContentItem, Slide } from "@/lib/types";
import axios from "axios";
import { uploadDirect } from "@uploadcare/upload-client";
import { openai, isOpenAIAvailable } from "@/lib/openai";


export const generateCreativePrompt = async (userPrompt: string) => {
  if (!isOpenAIAvailable() || !openai) {
    console.log("⚠️ OpenAI not configured - returning mock outline");
    // Return mock data for hackathon
    return {
      status: 200,
      data: {
        outlines: [
          `Introduction to ${userPrompt}`,
          "Background and Context",
          "Key Findings and Analysis",
          "Implications and Impact",
          "Recommendations",
          "Conclusion and Next Steps"
        ]
      }
    };
  }

  console.log("🟢 Generating creative prompt...", userPrompt);
  const finalPrompt = `
  Create a coherent and relevant outline for the following prompt: ${userPrompt}.
  The outline should consist of at least 6 points, with each point written as a single sentence.
  Ensure the outline is well-structured and directly related to the topic. 
  Return the output in the following JSON format:

  {
    "outlines": [
      "Point 1",
      "Point 2",
      "Point 3",
      "Point 4",
      "Point 5",
      "Point 6"
    ]
  }

  Ensure that the JSON is valid and properly formatted. Do not include any other text or explanations outside the JSON.
  `;

  try {
    const completion = await openai.chat.completions.create({
      model: "chatgpt-4o-latest",
      messages: [
        {
          role: "system",
          content:
            "You are a helpful AI that generates outlines for presentations.",
        },
        {
          role: "user",
          content: finalPrompt,
        },
      ],
      max_tokens: 1000,
      temperature: 0.0,
    });

    const responseContent = completion.choices[0]?.message?.content;

    if (responseContent) {
      try {
        const jsonResponse = JSON.parse(responseContent);
        return { status: 200, data: jsonResponse };
      } catch (err) {
        console.error("Invalid JSON received:", responseContent, err);
        return { status: 500, error: "Invalid JSON format received from AI" };
      }
    }

    return { status: 400, error: "No content generated" };
  } catch (error) {
    console.error("🔴 ERROR", error);
    return { status: 500, error: "Internal server error" };
  }
};


export const generateImages = async (slides: Slide[]) => {
  try {
    console.log("🟢 Generating images for slides...");

    // Create a deep clone to preserve original data
    const slidesCopy: Slide[] = JSON.parse(JSON.stringify(slides));

    // Process cloned slides
    const processedSlides = await Promise.all(
      slidesCopy.map(async (slide) => {
        const updatedContent = await processSlideContent(slide.content);
        return { ...slide, content: updatedContent };
      })
    );

    console.log("🟢 Images generated successfully");
    return { status: 200, data: processedSlides };
  } catch (error) {
    console.error("🔴 ERROR:", error);
    return { status: 500, error: "Internal server error" };
  }
};

const processSlideContent = async (content: ContentItem): Promise<ContentItem> => {
  // Create a deep clone of the content structure
  const contentClone: ContentItem = JSON.parse(JSON.stringify(content));
  const imageComponents = findImageComponents(contentClone);

  // Process images in parallel while maintaining structure
  await Promise.all(
    imageComponents.map(async (component) => {
      try {
        const newUrl = await generateImageUrl(component.alt || "Placeholder Image");
        component.content = newUrl;
      } catch (error) {
        console.error("🔴 Image generation failed:", error);
        component.content = "https://via.placeholder.com/1024";
      }
    })
  );

  return contentClone;
};

// Modified findImageComponents to work with cloned structure
const findImageComponents = (layout: ContentItem): ContentItem[] => {
  const images: ContentItem[] = [];

  const traverse = (node: ContentItem) => {
    if (node.type === "image") {
      images.push(node);
    }
    
    if (Array.isArray(node.content)) {
      node.content.forEach(child => traverse(child as ContentItem));
    } else if (typeof node.content === "object" && node.content !== null) {
      traverse(node.content);
    }
  };

  traverse(layout);
  return images;
};


const generateImageUrl = async (prompt: string): Promise<string> => {
  if (!isOpenAIAvailable() || !openai) {
    console.log("⚠️ OpenAI not configured - using placeholder image");
    return "https://via.placeholder.com/1024";
  }

  try {
    const improvedPrompt = `
    Create a highly realistic, professional image based on the following description. The image should look as if captured in real life, with attention to detail, lighting, and texture. 

    Description: ${prompt}

    Important Notes:
    - The image must be in a photorealistic style and visually compelling.
    - Ensure all text, signs, or visible writing in the image are in English.
    - Pay special attention to lighting, shadows, and textures to make the image as lifelike as possible.
    - Avoid elements that appear abstract, cartoonish, or overly artistic. The image should be suitable for professional presentations.
    - Focus on accurately depicting the concept described, including specific objects, environment, mood, and context. Maintain relevance to the description provided.

    Example Use Cases: Business presentations, educational slides, professional designs.
  `;
    const dalleResponse = await openai.images.generate({
      prompt: improvedPrompt,
      n: 1,
      size: "1024x1024",
    });
    console.log("🟢 Image generated successfully:", dalleResponse.data?.[0]?.url);
    const imageUrl = dalleResponse.data?.[0]?.url;
    if (!imageUrl) {
      console.error("Failed to generate image");
      return "https://via.placeholder.com/1024";
    }
    // Download the image from DALL·E
    const imageResponse = await axios.get(imageUrl, {
      responseType: "arraybuffer",
    });
    const imageBuffer = Buffer.from(imageResponse.data);
    const result = await uploadDirect(imageBuffer, {
      publicKey: process.env.UPLOADCARE_PUBLIC_KEY!,
      store: "auto",
    });

    console.log("🟢 Image uploaded to Uploadcare:", result?.uuid);

    return result?.uuid
      ? `https://ucarecdn.com/${result.uuid}/-/preview/`
      : "https://via.placeholder.com/1024";
  } catch (error) {
    console.error("Failed to generate image:", error);
    return "https://via.placeholder.com/1024";
  }
};
