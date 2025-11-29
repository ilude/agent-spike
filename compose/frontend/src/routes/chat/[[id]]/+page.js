/**
 * Page load function for chat route
 * Extracts conversation ID from URL params
 */
export function load({ params }) {
	return {
		conversationId: params.id || null
	};
}
