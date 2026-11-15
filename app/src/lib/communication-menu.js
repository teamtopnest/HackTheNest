const categories = {
  Food: {
    'Fast food': ['Pizza', 'Taco Bell', 'McDonald’s', 'Subway'],
    'Home cooked': ['Chicken and rice', 'Pasta', 'Roast dinner', 'Stew', 'Vegetarian meal', 'Fish and potatoes'],
    Snacks: ['Chips', 'Crackers', 'Nuts', 'Popcorn', 'Granola bar', 'Cheese'],
    Fruit: ['Apple', 'Banana', 'Orange', 'Grapes', 'Berries', 'Melon'],
    Soup: ['Chicken noodle', 'Tomato', 'Vegetable', 'Lentil', 'Mushroom', 'Beef broth'],
    Dessert: ['Ice cream', 'Cake', 'Cookies', 'Pudding', 'Pie', 'Yogurt'],
  },
  Drink: {
    Water: ['Tap water', 'Brita filtered', 'Evian', 'Dasani', 'Aquafina', 'Perrier'],
    Pop: ['Coca-Cola', 'Pepsi', 'Sprite', '7UP', 'Canada Dry', 'Fanta'],
    Juice: ['Tropicana', 'Minute Maid', 'Simply Orange', 'Ocean Spray', 'Apple juice', 'Fresh juice'],
    Tea: ['Tetley', 'Lipton', 'Twinings', 'Green tea', 'Peppermint tea', 'Decaf tea'],
    Coffee: ['Tim Hortons', 'Starbucks', 'Nescafé', 'Decaf coffee', 'Home brewed'],
    Milk: ['Dairy milk', 'Lactose-free milk', 'Silk soy', 'Oatly oat', 'Almond Breeze'],
  },
  Move: {
    Outside: ['Park', 'Home', 'Fresh air', 'Garden', 'Patio', 'Go for a walk'],
    Inside: ['Indoor walk', 'Bedroom', 'Living room', 'Kitchen', 'Bathroom', 'Hallway'],
    Reposition: ['Sit up', 'Lie down', 'Turn left', 'Turn right', 'Raise legs', 'Adjust pillow'],
    Transfer: ['To wheelchair', 'To bed', 'To chair', 'To standing', 'Need assistance'],
    Travel: ['Visit family', 'Visit friends', 'Car ride', 'Appointment', 'Shop'],
  },
  Pain: {
    Head: ['Forehead', 'Temples', 'Back of head', 'Face', 'Eyes', 'Jaw'],
    Torso: ['Chest', 'Upper back', 'Lower back', 'Abdomen', 'Ribs', 'Shoulders'],
    Arms: ['Left upper arm', 'Right upper arm', 'Left elbow', 'Right elbow', 'Forearm', 'Wrist'],
    'Lower limbs': ['Left hip', 'Right hip', 'Thigh', 'Knee', 'Calf', 'Shin'],
    Feet: ['Left ankle', 'Right ankle', 'Heel', 'Sole', 'Toes', 'Top of foot'],
    Hands: ['Left hand', 'Right hand', 'Palm', 'Fingers', 'Thumb'],
  },
  Help: {
    Toilet: ['Need to pee', 'Bowel movement', 'Help to bathroom', 'Bedpan', 'Urinal', 'Change pad'],
    Clothing: ['Change clothes', 'Shirt', 'Pants', 'Socks', 'Too tight', 'Too hot or cold'],
    Hygiene: ['Wash face', 'Brush teeth', 'Shower', 'Wash hands', 'Comb hair', 'Clean spill'],
    Comfort: ['Blanket', 'Pillow', 'Adjust temperature', 'Reduce noise', 'Dim lights', 'Rest'],
    'Eating assistance': ['Help eating', 'Help drinking', 'Cut food', 'Bring meal', 'Bring straw'],
    'Call someone': ['Caregiver', 'Nurse', 'Doctor', 'Family member', 'Friend', 'Urgent assistance'],
  },
  Family: {
    Parents: ['Mother', 'Father', 'Stepmother', 'Stepfather'],
    Siblings: ['Sister', 'Brother', 'Stepsister', 'Stepbrother'],
    Children: ['Daughter', 'Son', 'Granddaughter', 'Grandson'],
    Partner: ['Spouse', 'Partner', 'Fiancé', 'Fiancée'],
    'Extended family': ['Grandmother', 'Grandfather', 'Aunt', 'Uncle', 'Cousin'],
    'Contact family': ['Phone call', 'Video call', 'Send message', 'Ask for a visit', 'Share an update'],
  },
  Friends: {
    'Close friends': ['Best friend', 'Childhood friend', 'School friend', 'Family friend'],
    'Friend groups': ['Work friends', 'Neighbors', 'Sports friends', 'Community friends'],
    'Contact friends': ['Phone a friend', 'Video call a friend', 'Message a friend', 'Ask a friend to visit'],
    Activities: ['Chat together', 'Watch a movie', 'Listen to music', 'Play a game', 'Go out together'],
    Messages: ['Hello', 'Thank you', 'I miss you', 'Please visit', 'See you soon'],
  },
};

export const COMMUNICATION_MENU = {
  label: 'Home',
  children: [
    ...Object.entries(categories).map(([label, groups]) => ({
      label,
      children: [
        ...Object.entries(groups).map(([group, items]) => ({
          label: group,
          children: [...items, 'Other'].map((item) => ({ label: item })),
        })),
        { label: 'Other' },
      ],
    })),
    { label: 'Other' },
  ],
};

export function getFlashingRounds(menu) {
  return menu.children.some((item) => item.children) ? 4 : 5;
}
