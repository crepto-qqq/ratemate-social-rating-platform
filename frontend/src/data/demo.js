export const photos = {
  coffee: '1660144102328-68974117f580',
  travel: '1631045603628-7ea89c855daf',
  headphones: '1505740420928-5e560c06d30e',
  food: '1622237809627-fc160f2ca120',
  architecture: '1690283978974-f7f63af54ea7',
  camera: '1518353053542-7ea33d942319',
}

export const topics = {
  coffee: {
    criteria: [['Flavor', 3], ['Aroma', 2], ['Value', 1]],
    items: ['Flat white', 'Cappuccino', 'Pour-over', 'Espresso', 'Cold brew', 'Latte', 'Long black', 'Mocha'],
    description: 'My personal search for a coffee worth slowing down for. I rated each cup on flavor, aroma, and value, with a little extra weight on how it tastes.',
  },
  travel: {
    criteria: [['Scenery', 3], ['Trail experience', 2], ['Accessibility', 1]],
    items: ['Alpine ridge', 'Lakeside loop', 'Forest path', 'Summit walk', 'Valley trail', 'Coastal track', 'Waterfall walk', 'Meadow loop', 'Clifftop path', 'River crossing', 'Lookout trail', 'Woodland circuit'],
    description: 'A collection of walks I would happily take again. These ratings balance the views, the walking experience, and how easy it is to reach the trail.',
  },
  headphones: {
    criteria: [['Sound', 3], ['Comfort', 2], ['Value', 1]],
    items: ['Studio over-ear', 'Everyday wireless', 'Travel noise-cancelling', 'Lightweight on-ear', 'Open-back reference', 'Compact earbuds'],
    description: 'A personal listening shortlist for work, travel, and quiet evenings. Sound comes first, but comfort and value deserve a place in the decision too.',
  },
  food: {
    criteria: [['Taste', 3], ['Texture', 2], ['Value', 1]],
    items: ['Avocado toast', 'Pancakes', 'Eggs on sourdough', 'Breakfast bowl', 'French toast', 'Mushroom toast', 'Breakfast sandwich', 'Granola bowl', 'Waffles', 'Seasonal salad'],
    description: 'The dishes I keep thinking about after the weekend. I rated taste, texture, and value to find the ones I would order again.',
  },
  architecture: {
    criteria: [['Design', 3], ['Atmosphere', 2], ['Detail', 1]],
    items: ['Courtyard house', 'City library', 'Gallery entrance', 'Brick townhouse', 'Garden pavilion', 'Corner café', 'Riverside museum', 'Station hall', 'Atrium'],
    description: 'Spaces that made me pause and look a little closer. My ratings reflect their design, atmosphere, and the care in the smallest details.',
  },
  camera: {
    criteria: [['Image quality', 3], ['Handling', 2], ['Portability', 1]],
    items: ['Everyday compact', 'Classic film camera', 'Travel mirrorless', 'Studio camera', 'Pocket camera', 'Weekend rangefinder'],
    description: 'A personal camera shortlist, considering both the images and the experience of making them.',
  },
}

export const templates = [
  ['The search for my perfect morning coffee', 'coffee', 'Food & drink', 'Olivia Chen', 128, 8, 1.04],
  ['A little escape: trails worth the early start', 'travel', 'Outdoors', 'Alex Morgan', 246, 12, 1.23],
  ['Headphones for getting lost in the music', 'headphones', 'Tech', 'Noah Williams', 89, 6, .9],
  ['Weekend brunch, honestly rated', 'food', 'Food & drink', 'Sophie Lee', 312, 10, 1.24],
  ['Buildings that made me stop and look up', 'architecture', 'Design', 'Ethan Brooks', 174, 9, 1.3],
  ['My everyday camera shortlist', 'camera', 'Photography', 'Lucas Martin', 96, 5, .95],
  ['Good coffee. Better conversations.', 'coffee', 'Food & drink', 'Mia Wilson', 207, 7, 1.27],
  ['Finding quiet, one mountain at a time', 'travel', 'Travel', 'Isabella Ross', 428, 8, 1.08],
  ['Sound, comfort, and everything in between', 'headphones', 'Tech', 'Oliver James', 153, 4, 1.03],
  ['Small details, remarkable spaces', 'architecture', 'Design', 'Amelia Davis', 267, 9, 1.34],
  ['The cameras I keep coming back to', 'camera', 'Photography', 'Henry Kim', 118, 6, 1.1],
  ['A very personal guide to comfort food', 'food', 'Food & drink', 'Charlotte Wu', 354, 9, .96],
]

export function photoUrl(topic, width = 900) {
  return `https://images.unsplash.com/photo-${photos[topic]}?auto=format&fit=crop&w=${width}&q=85`
}

export function templateDetail(id) {
  const template = templates[id]
  if (!template) return null
  const topic = topics[template[1]]
  const criteria = topic.criteria.map(([name, weight]) => ({ name, weight }))
  const items = topic.items.slice(0, template[5]).map((name, itemIndex) => {
    const ratings = criteria.map((_, criterionIndex) => 3 + ((itemIndex * 2 + criterionIndex + id) % 3))
    const totalWeight = criteria.reduce((sum, criterion) => sum + Math.abs(criterion.weight), 0)
    const score = criteria.reduce((sum, criterion, index) => sum + ratings[index] * criterion.weight, 0) / totalWeight * 20
    return { name, ratings, score }
  })
  return { template, criteria, items, description: topic.description }
}

export const notifications = [
  { id: 1, type: 'comment', actor: 'Olivia Chen', template: 'My weekend coffee shortlist', date: 'Today, 4:40 pm', text: 'Love that you gave flavor the most weight. I would like to try this with my local cafés.' },
  { id: 2, type: 'like', actor: 'Alex Morgan', template: 'Walks I would take again', date: 'Today, 3:15 pm' },
  { id: 3, type: 'comment', actor: 'Noah Williams', template: 'My everyday camera picks', date: 'Today, 12:30 pm', text: 'Handling makes such a difference. The smaller camera is the one I actually take out with me.' },
  { id: 4, type: 'like', actor: 'Sophie Lee', template: 'My weekend coffee shortlist', date: 'Yesterday, 10:50 pm' },
  { id: 5, type: 'comment', actor: 'Ethan Brooks', template: 'Walks I would take again', date: 'Yesterday, 7:20 am', text: 'The lakeside loop deserves its spot.' },
]
