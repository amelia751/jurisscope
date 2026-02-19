import { TabsContent } from "@/components/ui/tabs";
import React from "react";
import { Projects } from "../projects";

export const TabsContentComponent = () => {
  return (
    <React.Fragment>
      <TabsContent value="all">
        <Projects arrayLength={12} />
      </TabsContent>
      <TabsContent value="recent">
        <Projects arrayLength={8} />
      </TabsContent>
      <TabsContent value="shared">
        <Projects arrayLength={4} />
      </TabsContent>
    </React.Fragment>
  );
};



import ProjectCard from "../project-card";

type Props = {
  arrayLength: number;
  isDelete?: boolean;
};

export const Projects = ({ arrayLength, isDelete = false }: Props) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: arrayLength }).map((_, i) => (
        <ProjectCard
          key={i}
          title="Abraham Maslow's Hierarchy of Needs Criticism"
          description="Created 1m ago"
          src="https://plus.unsplash.com/premium_photo-1729004379397-ece899804701?q=80&w=2767&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
          isDelete={isDelete}
        />
      ))}
    </div>
  );
};




import { containerVariants, itemVariants } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { motion } from "framer-motion";

export const RecentPrompts = () => {
  return (
    <motion.div variants={containerVariants} className="space-y-4 !mt-20">
      <motion.h2 variants={itemVariants} className="text-2xl font-semibold text-center">
        Your Recent Prompts
      </motion.h2>
      <motion.div
        variants={containerVariants}
        className="space-y-2 w-full md:max-w-[50%] mx-auto"
      >
        {Array.from({ length: 5 }).map((_, i) => (
          <motion.div key={i} variants={itemVariants}>
            <Card className="p-4 flex items-center justify-between hover:bg-accent/50 transition-colors duration-300">
              <div>
                <h3 className="font-medium">Marketing Analysis</h3>
                <p className="text-sm text-muted-foreground">2m ago</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-clause">Creative AI</span>

                <Button variant="default" size="sm" className="rounded-xl bg-primary-20 text-primary">
                  Standard
                </Button>

                <Button variant="default" size="sm" className="rounded-xl bg-primary-20 text-primary">
                  Edit
                </Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
};









import React, { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "./Card";
import { OutlineCard } from "@/lib/types";
import { AddCardButton } from "./AddCardButton";

interface CardListProps {
  cards: OutlineCard[];
  editingCard: string | null;
  selectedCard: string | null;
  editText: string;
  setCards: (cards: OutlineCard[]) => void;
  onEditChange: (value: string) => void;
  onCardSelect: (id: string) => void;
  onCardDoubleClick: (id: string, title: string) => void;
  setEditText: (value: string) => void;
  setEditingCard: (id: string | null) => void;
  setSelectedCard: (id: string | null) => void;
}

export const CardList: React.FC<CardListProps> = ({
  cards,
  editingCard,
  selectedCard,
  editText,
  setCards,
  setEditText,
  setEditingCard,
  setSelectedCard,
  onEditChange,
  onCardSelect,
  onCardDoubleClick,
}) => {
  const [draggedItem, setDraggedItem] = useState<OutlineCard | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const dragOffsetY = useRef<number>(0);

  const getDragOverStyles = (cardIndex: number) => {
    if (dragOverIndex === null || draggedItem === null) return {};
    if (cardIndex === dragOverIndex) {
      return {
        borderTop: "2px solid #000",
        marginTop: "0.5rem",
        transition: "margin 0.2s cubic-bezier(0.25, 0.1, 0.25, 1)",
      };
    } else if (cardIndex === dragOverIndex - 1) {
      return {
        borderBottom: "2px solid #000",
        marginBottom: "0.5rem",
        transition: "margin 0.2s cubic-bezier(0.25, 0.1, 0.25, 1)",
      };
    }
    return {};
  };

  const onAddCard = (index?: number) => {
    const newCard: OutlineCard = {
      id: Math.random().toString(36).substr(2, 9),
      title: editText || "New Section",
      order: (index !== undefined ? index : cards.length) + 1,
    };

    const updatedCards =
      index !== undefined
        ? [
            ...cards.slice(0, index + 1),
            newCard,
            ...cards
              .slice(index + 1)
              .map((card) => ({ ...card, order: card.order + 1 })),
          ]
        : [...cards, newCard];

    setCards(updatedCards);
    setEditText("");
  };

  const onCardDelete = (id: string) => {
    setCards(
      cards
        .filter((card) => card.id !== id)
        .map((card, index) => ({ ...card, order: index + 1 }))
    );
  };

  const onCardUpdate = (id: string, newTitle: string) => {
    setCards(
      cards.map((card) =>
        card.id === id ? { ...card, title: newTitle } : card
      )
    );
    setEditingCard(null);
    setSelectedCard(null);
    setEditText("");
  };

  // const resetCards = () => {
  //   setCards([]);
  //   setEditingCard(null);
  //   setSelectedCard(null);
  //   setEditText("");
  // };

  const onDragStart = (e: React.DragEvent, card: OutlineCard) => {
    setDraggedItem(card);
    e.dataTransfer.effectAllowed = "move";

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    dragOffsetY.current = e.clientY - rect.top;

    const draggedEl = e.currentTarget.cloneNode(true) as HTMLElement;
    draggedEl.style.position = "absolute";
    draggedEl.style.top = "-1000px";
    draggedEl.style.opacity = "0.8";
    draggedEl.style.width = `${(e.currentTarget as HTMLElement).offsetWidth}px`;
    document.body.appendChild(draggedEl);

    e.dataTransfer.setDragImage(draggedEl, 0, dragOffsetY.current);

    setTimeout(() => {
      setDragOverIndex(cards.findIndex((c) => c.id === card.id));
      document.body.removeChild(draggedEl);
    }, 0);
  };

  const onDragEnd = () => {
    setDraggedItem(null);
    setDragOverIndex(null);
  };

  const onDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (!draggedItem) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const threshold = rect.height / 2;

    if (y < threshold) {
      setDragOverIndex(index);
    } else {
      setDragOverIndex(index + 1);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (!draggedItem || dragOverIndex === null) return;

    const updatedCards = [...cards];
    const draggedIndex = updatedCards.findIndex(
      (card) => card.id === draggedItem.id
    );

    if (draggedIndex === -1 || draggedIndex === dragOverIndex) return;

    const [removedCard] = updatedCards.splice(draggedIndex, 1);
    updatedCards.splice(
      dragOverIndex > draggedIndex ? dragOverIndex - 1 : dragOverIndex,
      0,
      removedCard
    );

    setCards(
      updatedCards.map((card, index) => ({ ...card, order: index + 1 }))
    );
    setDraggedItem(null);
    setDragOverIndex(null);
  };

  return (
    <motion.div
      className="space-y-4 -my-2"
      layout
      onDragOver={(e) => {
        e.preventDefault();
        if (
          cards.length === 0 ||
          e.clientY > e.currentTarget.getBoundingClientRect().bottom - 20
        ) {
          onDragOver(e, cards.length);
        }
      }}
      onDrop={(e) => {
        e.preventDefault();
        onDrop(e);
      }}
    >
      <AnimatePresence>
        {cards.map((card, index) => (
          <React.Fragment key={card.id}>
            <Card
              onDragOver={(e) => onDragOver(e, index)}
              card={card}
              isEditing={editingCard === card.id}
              isSelected={selectedCard === card.id}
              editText={editText}
              onEditChange={onEditChange}
              onEditBlur={() => onCardUpdate(card.id, editText)}
              onEditKeyDown={(e) => {
                if (e.key === "Enter") {
                  onCardUpdate(card.id, editText);
                }
              }}
              onCardClick={() => onCardSelect(card.id)}
              onCardDoubleClick={() => onCardDoubleClick(card.id, card.title)}
              onDeleteClick={() => onCardDelete(card.id)}
              dragHandlers={{
                onDragStart: (e) => onDragStart(e, card),
                onDragEnd: onDragEnd,
              }}
              dragOverStyles={getDragOverStyles(index)}
            />
            <AddCardButton onAddCard={() => onAddCard(index)} />
          </React.Fragment>
        ))}
      </AnimatePresence>
    </motion.div>
  );
};
